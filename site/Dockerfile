# ---------- build stage ----------
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json ./
COPY package-lock.json* yarn.lock* pnpm-lock.yaml* . 2>/dev/null || true
RUN npm install --foreground-scripts

COPY . .
RUN npm run build                 # outputs to /app/dist

# ---------- production stage ----------
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
