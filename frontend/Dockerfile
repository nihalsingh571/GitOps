# Single-stage — NGINX Alpine is already tiny (~25 MB)
FROM nginx:1.27-alpine

# Remove the default NGINX config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our reverse-proxy config
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy static frontend files
COPY index.html /usr/share/nginx/html/index.html

# NGINX listens on port 80 inside the container
EXPOSE 80

# Default CMD from base image starts NGINX in foreground — we keep it
