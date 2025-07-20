# site/Dockerfile
# ---------- build stage ----------
FROM node:20-alpine AS build

WORKDIR /app

# copy just package.json so Docker can cache 'npm install'
COPY package.json ./

# install deps (will read package-lock.json if you add it later)
RUN npm install --foreground-scripts

# now bring in the rest of your source
COPY . .

# build into /app/dist
RUN npm run build

# ---------- production stage ----------
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
