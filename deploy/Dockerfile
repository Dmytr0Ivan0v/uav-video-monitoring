FROM node:24.22-alpine AS build
WORKDIR /site
COPY site/package.json site/package-lock.json site/.npmrc ./
RUN npm ci
COPY site/ ./
RUN npm run build
# .gz next to each text file and the model for gzip_static; fonts and images are compressed already
RUN find dist -type f -size +1k \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.json' \
      -o -name '*.svg' -o -name '*.wasm' -o -name '*.onnx' \) -exec gzip -9 -k {} +

FROM nginx:1.30-alpine
COPY deploy/nginx/site.conf /etc/nginx/conf.d/default.conf
COPY --from=build /site/dist /usr/share/nginx/html
