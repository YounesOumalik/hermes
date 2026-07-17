FROM node:22-slim

WORKDIR /app

# Build arg pour l'URL publique du daemon
ARG NEXT_PUBLIC_DAEMON_URL=http://169.58.30.70:8001
ENV NEXT_PUBLIC_DAEMON_URL=${NEXT_PUBLIC_DAEMON_URL}

# Install dependencies based on package manager
COPY package*.json ./
RUN npm ci --omit=dev || npm install --omit=dev

# Copy source
COPY . .

# Build Next.js app (NEXT_PUBLIC_* are inlined at build time)
RUN npm run build

EXPOSE 3000

ENV NODE_ENV=production

CMD ["npm", "start"]
