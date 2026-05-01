# Build context: chat-ui/ (directory containing this Dockerfile + fly.toml).
# From repo root: fly deploy --config chat-ui/fly.toml

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_AGENT_BASE_URL=""
ENV VITE_AGENT_BASE_URL=${VITE_AGENT_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
