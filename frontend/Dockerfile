FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Sub-path the app is published under behind the host proxy, e.g. /signature. "/" = site root.
ARG BASE_PATH=/
RUN BASE="${BASE_PATH%/}" && VITE_BASE_PATH="$BASE/" VITE_API_BASE_URL="$BASE" npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
