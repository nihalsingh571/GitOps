import os
import re
import sys
from groq import Groq

def redact_sensitive_data(log_content):
    """
    Redacts anything matching common secret patterns.
    Why this matters: Logs can accidentally print environment variables, API keys, 
    or database passwords (e.g. during a crash dump). We must air-gap our secrets 
    from third-party LLM providers.
    """
    patterns = [
        # AWS Key like
        (r'AKIA[0-9A-Z]{16}', '<REDACTED_AWS_KEY>'),
        # Bearer tokens
        (r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', 'Bearer <REDACTED_TOKEN>'),
        # Generic passwords in URLs (e.g., postgres://user:password@host)
        (r':[^:@]+@', ':<REDACTED_PASSWORD>@'),
        # Common key formats (sk_test, pk_live, etc)
        (r'(sk|pk)_(test|live)_[0-9a-zA-Z]{24,34}', '<REDACTED_API_KEY>'),
        # High entropy hex/base64 strings that might be secrets (simplified for this demo)
        (r'(?i)api_key[\s=:\'"]+[A-Za-z0-9\-_]{20,}', 'api_key=<REDACTED_API_KEY>'),
        (r'(?i)password[\s=:\'"]+[^&\s\'"]+', 'password=<REDACTED_PASSWORD>')
    ]
    
    redacted_log = log_content
    for pattern, replacement in patterns:
        redacted_log = re.sub(pattern, replacement, redacted_log)
        
    return redacted_log

def truncate_log(log_content, max_chars=15000):
    """
    Truncates the log to the last `max_chars`.
    Why: CI logs can be megabytes long. LLMs have context limits (e.g., 32k tokens), 
    and sending massive logs wastes API budget/tokens and increases latency. The actual 
    failure is almost always at the very end of the log.
    """
    if len(log_content) > max_chars:
        return "... [TRUNCATED] ...\n" + log_content[-max_chars:]
    return log_content

def analyze_log(log_content):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set.")
        sys.exit(1)
        
    client = Groq(api_key=api_key)
    
    # Why this prompt works:
    # A vague prompt like "Fix this code" returns a generic, unhelpful essay.
    # We strictly enforce output format, require line numbers, and demand actionable steps.
    prompt = f"""
You are a senior DevOps engineer diagnosing a CI pipeline failure.
Read the following CI log and provide a highly focused diagnosis.

Format your response EXACTLY as follows in Markdown:

### 🚨 CI Failure Diagnosis
**Likely Root Cause:** [1-2 sentences explaining what failed and why]

**Implicated File/Command:** [Specific file, line number, or script command if found]

**Suggested Fix:**
[Concrete steps or code snippet to resolve the issue]

Log Content:
```
{log_content}
```
"""

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", # Extremely fast and free tier friendly
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, # Low temperature for more deterministic, factual analysis
        )
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Expect the log file path as the first argument
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <path_to_log_file>")
        sys.exit(1)
        
    log_file_path = sys.argv[1]
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        sys.exit(1)
        
    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_log = f.read()
        
    redacted = redact_sensitive_data(raw_log)
    truncated = truncate_log(redacted)
    
    analyze_log(truncated)
