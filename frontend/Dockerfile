FROM node:20-alpine AS build
WORKDIR /app

# Build-time public config (Vite bakes these into the bundle).
ARG VITE_API_BASE=http://localhost:8000/api/v1
ARG VITE_TELEGRAM_BOT=
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_TELEGRAM_BOT=$VITE_TELEGRAM_BOT

COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
