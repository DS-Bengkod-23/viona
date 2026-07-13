#!/bin/bash
set -e

cd /app

if [ ! -d "vendor" ]; then
    echo "Installing Composer dependencies..."
    composer install --no-interaction
fi

if [ ! -d "node_modules" ]; then
    echo "Installing NPM dependencies..."
    npm install
fi

if [ ! -d "public/build" ]; then
    echo "Building Vite assets..."
    npm run build
fi

echo "Starting Laravel server..."
exec php artisan serve --host=0.0.0.0 --port=8002
