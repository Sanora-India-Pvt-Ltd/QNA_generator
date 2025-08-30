<?php
// LMS Setup Script
echo "=== Learning Management System Setup ===\n\n";

// Check PHP version
if (version_compare(PHP_VERSION, '7.4.0', '<')) {
    echo "❌ Error: PHP 7.4 or higher is required. Current version: " . PHP_VERSION . "\n";
    exit(1);
}
echo "✅ PHP version: " . PHP_VERSION . "\n";

// Check required extensions
$required_extensions = ['pdo', 'pdo_mysql', 'openssl', 'mbstring', 'json'];
foreach ($required_extensions as $ext) {
    if (!extension_loaded($ext)) {
        echo "❌ Error: PHP extension '$ext' is not loaded.\n";
        exit(1);
    }
}
echo "✅ All required PHP extensions are loaded.\n";

// Create .env file if it doesn't exist
if (!file_exists('.env')) {
    echo "\n📝 Creating .env file...\n";
    $env_content = "# Database Configuration
DB_HOST=localhost
DB_NAME=lms_db
DB_USER=root
DB_PASS=

# Stripe Configuration (optional for demo)
STRIPE_PUBLISHABLE_KEY=pk_test_mock_key
STRIPE_SECRET_KEY=sk_test_mock_key

# Email Configuration (optional for demo)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Application Configuration
APP_URL=http://localhost/php
APP_NAME=\"Learning Management System\"
APP_ENV=development
";
    
    if (file_put_contents('.env', $env_content)) {
        echo "✅ .env file created successfully.\n";
        echo "⚠️  Please edit .env file with your database credentials.\n";
    } else {
        echo "❌ Error: Could not create .env file.\n";
    }
} else {
    echo "✅ .env file already exists.\n";
}

// Test database connection
echo "\n🔍 Testing database connection...\n";
try {
    // Load environment variables
    if (file_exists('.env')) {
        $env = parse_ini_file('.env');
        foreach ($env as $key => $value) {
            $_ENV[$key] = $value;
        }
    }
    
    $host = $_ENV['DB_HOST'] ?? 'localhost';
    $dbname = $_ENV['DB_NAME'] ?? 'lms_db';
    $username = $_ENV['DB_USER'] ?? 'root';
    $password = $_ENV['DB_PASS'] ?? '';
    
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "✅ Database connection successful.\n";
    
    // Check if tables exist
    $tables = $pdo->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
    if (empty($tables)) {
        echo "⚠️  No tables found in database. Please import the database schema.\n";
        echo "   Run: mysql -u $username -p $dbname < database/schema.sql\n";
    } else {
        echo "✅ Database tables found: " . count($tables) . " tables\n";
    }
    
} catch (PDOException $e) {
    echo "❌ Database connection failed: " . $e->getMessage() . "\n";
    echo "   Please check your database credentials in .env file.\n";
}

// Create uploads directory
if (!is_dir('uploads')) {
    if (mkdir('uploads', 0777, true)) {
        echo "✅ Uploads directory created.\n";
    } else {
        echo "❌ Error: Could not create uploads directory.\n";
    }
} else {
    echo "✅ Uploads directory exists.\n";
}

echo "\n=== Setup Complete ===\n";
echo "Next steps:\n";
echo "1. Edit .env file with your database credentials\n";
echo "2. Import database schema: mysql -u username -p lms_db < database/schema.sql\n";
echo "3. Access the application at: http://localhost/php\n";
echo "4. Login with: admin / password\n";
echo "\n";
?>
