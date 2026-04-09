# Stage 1: build
FROM node:22-alpine AS builder
WORKDIR /app

# Copy manifests and install — use npm install instead of npm ci
# to avoid lockfile version incompatibilities between local npm 11
# and whatever npm ships in the base image
COPY package.json ./
RUN npm install --legacy-peer-deps

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
