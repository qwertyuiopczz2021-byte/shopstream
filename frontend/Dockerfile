FROM nginx:1.27-alpine

# The page and the proxy live in the same container on purpose: the browser only
# ever talks to one origin, so there is no CORS preflight anywhere in the system.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY public/ /usr/share/nginx/html/

EXPOSE 80
