# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Coppy package files và cài đặt
COPY package*.json ./
RUN npm install

# Copy source code và build
COPY . .
# Chú ý: VITE_API_URL có thể được truyền vào lúc build hoặc qua env runtime nếu dùng script đặc biệt
# Ở đây chúng ta build tĩnh.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Serve với Nginx
FROM nginx:stable-alpine

# Copy file build từ Stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Copy cấu hình Nginx (SPA support)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
