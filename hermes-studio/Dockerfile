FROM node:22-slim

WORKDIR /app

# Install dependencies based on package manager
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

RUN npm run build

# Next.js standalone does not copy static assets automatically.
RUN mkdir -p .next/standalone/.next \
    && cp -r .next/static .next/standalone/.next/static \
    && if [ -d public ]; then cp -r public .next/standalone/public; fi

EXPOSE 3000

ENV NODE_ENV=production

ENV HOSTNAME=0.0.0.0
CMD ["node", ".next/standalone/server.js"]
