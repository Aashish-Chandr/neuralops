# Stage 1: build
# node:22-alpine ships with npm 10+ which handles lockfileVersion 3
FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

COPY . .
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV PORT=80
ENV API_GATEWAY_PORT=8090

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
