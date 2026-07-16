FROM php:8.2-cli

# Install dependencies needed for Composer and Node
RUN apt-get update && apt-get install -y \
    git \
    unzip \
    curl \
    libzip-dev \
    && docker-php-ext-install zip \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Install Node.js (v20) and npm
# NodeSource's nodejs package only ships corepack shims, not a direct `npm`
# binary — `corepack enable npm` links /usr/bin/npm so `npm install`/`npm run
# build` in start.sh actually resolve.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable npm

WORKDIR /app

# Copy the start script
COPY docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

ENTRYPOINT ["/usr/local/bin/start.sh"]
