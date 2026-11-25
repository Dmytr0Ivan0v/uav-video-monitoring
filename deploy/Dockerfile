FROM node:24.22-alpine AS build
WORKDIR /site
COPY site/package.json site/package-lock.json site/.npmrc ./
RUN npm ci
COPY site/ ./
RUN npm run build

FROM nginx:1.30-alpine
COPY deploy/nginx/site.conf /etc/nginx/conf.d/default.conf
COPY --from=build /site/dist /usr/share/nginx/html
