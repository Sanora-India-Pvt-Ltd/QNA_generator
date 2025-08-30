<?php

// Load environment variables
if (file_exists(__DIR__ . '/../.env')) {
    $env = parse_ini_file(__DIR__ . '/../.env');
    foreach ($env as $key => $value) {
        $_ENV[$key] = $value;
    }
}

// Error reporting
if ($_ENV['APP_ENV'] === 'development') {
    error_reporting(E_ALL);
    ini_set('display_errors', 1);
} else {
    error_reporting(0);
    ini_set('display_errors', 0);
}

// Session configuration
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    ini_set('session.use_only_cookies', 1);
    session_start();
}

// Timezone
date_default_timezone_set('UTC');

// Constants
define('APP_ROOT', dirname(__DIR__));
define('APP_URL', $_ENV['APP_URL'] ?? 'http://localhost/lms');
define('APP_NAME', $_ENV['APP_NAME'] ?? 'Learning Management System');

// Autoloader
spl_autoload_register(function ($class) {
    $file = APP_ROOT . '/src/' . str_replace('\\', '/', $class) . '.php';
    if (file_exists($file)) {
        require_once $file;
    }
});

// Load core classes
require_once APP_ROOT . '/config/database.php';
require_once APP_ROOT . '/src/Auth.php';
require_once APP_ROOT . '/src/User.php';
require_once APP_ROOT . '/src/Course.php';
require_once APP_ROOT . '/src/Lesson.php';
require_once APP_ROOT . '/src/Quiz.php';
require_once APP_ROOT . '/src/Payment.php';

// Helper functions
function redirect($url) {
    header("Location: $url");
    exit();
}

function asset($path) {
    return APP_URL . '/assets/' . ltrim($path, '/');
}

function csrf_token() {
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verify_csrf_token($token) {
    return isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token);
}

function sanitize($input) {
    return htmlspecialchars($input, ENT_QUOTES, 'UTF-8');
}

function format_price($price) {
    return '$' . number_format($price, 2);
}

function format_duration($minutes) {
    $hours = floor($minutes / 60);
    $mins = $minutes % 60;
    
    if ($hours > 0) {
        return $hours . 'h ' . $mins . 'm';
    }
    return $mins . 'm';
}
