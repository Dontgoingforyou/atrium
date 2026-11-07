# Softgen delivery / split layout: контекст сборки — каталог frontend/
# (корневой deploy/docker/Dockerfile.web собирается из корня monorepo)
FROM node:22-bookworm AS frontend-build
WORKDIR /build
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /build/dist /usr/share/nginx/html
EXPOSE 80
