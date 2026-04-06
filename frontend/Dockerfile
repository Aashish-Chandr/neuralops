# Stage 1: build React app
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve with nginx
# Railway injects $PORT — we use envsubst to inject it into nginx.conf at startup
FROM nginx:alpine
RUN apk add --no-cache bash

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

# nginx official image runs envsubst on /etc/nginx/templates/*.template
# and writes the result to /etc/nginx/conf.d/ before starting
ENV PORT=80
ENV API_GATEWAY_PORT=8090

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
