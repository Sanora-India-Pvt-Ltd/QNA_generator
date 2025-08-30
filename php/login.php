<?php
require_once 'config/config.php';

$auth = new Auth();

// Redirect if already logged in
if ($auth->isLoggedIn()) {
    redirect('/dashboard.php');
}

$error = '';
$success = '';

// Handle login form submission
if ($_POST && isset($_POST['login'])) {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    
    if (empty($username) || empty($password)) {
        $error = 'Please enter both username and password';
    } else {
        $result = $auth->login($username, $password);
        if ($result['success']) {
            redirect('/dashboard.php');
        } else {
            $error = $result['message'];
        }
    }
}

// Handle registration form submission
if ($_POST && isset($_POST['register'])) {
    $data = [
        'username' => $_POST['username'] ?? '',
        'email' => $_POST['email'] ?? '',
        'password' => $_POST['password'] ?? '',
        'first_name' => $_POST['first_name'] ?? '',
        'last_name' => $_POST['last_name'] ?? '',
        'role' => 'student'
    ];
    
    // Validate required fields
    if (empty($data['username']) || empty($data['email']) || empty($data['password']) || 
        empty($data['first_name']) || empty($data['last_name'])) {
        $error = 'All fields are required';
    } elseif (strlen($data['password']) < 6) {
        $error = 'Password must be at least 6 characters long';
    } elseif (!filter_var($data['email'], FILTER_VALIDATE_EMAIL)) {
        $error = 'Please enter a valid email address';
    } else {
        $result = $auth->register($data);
        if ($result['success']) {
            $success = $result['message'];
        } else {
            $error = $result['message'];
        }
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="assets/css/style.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container">
        <div class="row justify-content-center align-items-center min-vh-100">
            <div class="col-md-8 col-lg-6">
                <div class="card shadow-lg">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <h2 class="fw-bold text-primary"><?= APP_NAME ?></h2>
                            <p class="text-muted">Sign in to your account or create a new one</p>
                        </div>

                        <?php if ($error): ?>
                        <div class="alert alert-danger"><?= htmlspecialchars($error) ?></div>
                        <?php endif; ?>

                        <?php if ($success): ?>
                        <div class="alert alert-success"><?= htmlspecialchars($success) ?></div>
                        <?php endif; ?>

                        <!-- Login Form -->
                        <div id="loginForm">
                            <h4 class="mb-3">Sign In</h4>
                            <form method="POST" action="">
                                <div class="mb-3">
                                    <label for="username" class="form-label">Username or Email</label>
                                    <input type="text" class="form-control" id="username" name="username" required>
                                </div>
                                <div class="mb-3">
                                    <label for="password" class="form-label">Password</label>
                                    <input type="password" class="form-control" id="password" name="password" required>
                                </div>
                                <div class="d-grid">
                                    <button type="submit" name="login" class="btn btn-primary">Sign In</button>
                                </div>
                            </form>
                            <div class="text-center mt-3">
                                <p class="mb-0">Don't have an account? <a href="#" onclick="showRegister()">Sign up</a></p>
                            </div>
                        </div>

                        <!-- Registration Form -->
                        <div id="registerForm" style="display: none;">
                            <h4 class="mb-3">Create Account</h4>
                            <form method="POST" action="">
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label for="first_name" class="form-label">First Name</label>
                                        <input type="text" class="form-control" id="first_name" name="first_name" required>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label for="last_name" class="form-label">Last Name</label>
                                        <input type="text" class="form-control" id="last_name" name="last_name" required>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="reg_username" class="form-label">Username</label>
                                    <input type="text" class="form-control" id="reg_username" name="username" required>
                                </div>
                                <div class="mb-3">
                                    <label for="reg_email" class="form-label">Email</label>
                                    <input type="email" class="form-control" id="reg_email" name="email" required>
                                </div>
                                <div class="mb-3">
                                    <label for="reg_password" class="form-label">Password</label>
                                    <input type="password" class="form-control" id="reg_password" name="password" required>
                                    <div class="form-text">Password must be at least 6 characters long</div>
                                </div>
                                <div class="d-grid">
                                    <button type="submit" name="register" class="btn btn-success">Create Account</button>
                                </div>
                            </form>
                            <div class="text-center mt-3">
                                <p class="mb-0">Already have an account? <a href="#" onclick="showLogin()">Sign in</a></p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="text-center mt-3">
                    <a href="index.php" class="text-decoration-none">
                        <i class="fas fa-arrow-left"></i> Back to Home
                    </a>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function showRegister() {
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('registerForm').style.display = 'block';
        }
        
        function showLogin() {
            document.getElementById('registerForm').style.display = 'none';
            document.getElementById('loginForm').style.display = 'block';
        }
    </script>
</body>
</html>
