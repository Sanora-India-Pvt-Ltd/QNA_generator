<?php
$auth = new Auth();
$currentUser = $auth->getCurrentUser();
?>

<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container">
        <a class="navbar-brand fw-bold" href="index.php">
            <i class="fas fa-graduation-cap me-2"></i><?= APP_NAME ?>
        </a>
        
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
                <li class="nav-item">
                    <a class="nav-link" href="index.php">Home</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="courses.php">Courses</a>
                </li>
                <?php if ($auth->isLoggedIn()): ?>
                <li class="nav-item">
                    <a class="nav-link" href="dashboard.php">Dashboard</a>
                </li>
                <?php if ($auth->isTeacher()): ?>
                <li class="nav-item">
                    <a class="nav-link" href="instructor/courses.php">My Courses</a>
                </li>
                <?php endif; ?>
                <?php if ($auth->isAdmin()): ?>
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" id="adminDropdown" role="button" data-bs-toggle="dropdown">
                        Admin
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="admin/users.php">Users</a></li>
                        <li><a class="dropdown-item" href="admin/courses.php">All Courses</a></li>
                        <li><a class="dropdown-item" href="admin/payments.php">Payments</a></li>
                        <li><a class="dropdown-item" href="admin/reports.php">Reports</a></li>
                    </ul>
                </li>
                <?php endif; ?>
                <?php endif; ?>
            </ul>
            
            <ul class="navbar-nav">
                <?php if ($auth->isLoggedIn()): ?>
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">
                        <i class="fas fa-user-circle me-1"></i>
                        <?= htmlspecialchars($currentUser['first_name'] . ' ' . $currentUser['last_name']) ?>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item" href="profile.php">Profile</a></li>
                        <li><a class="dropdown-item" href="my-courses.php">My Courses</a></li>
                        <li><a class="dropdown-item" href="certificates.php">Certificates</a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="logout.php">Sign Out</a></li>
                    </ul>
                </li>
                <?php else: ?>
                <li class="nav-item">
                    <a class="nav-link" href="login.php">Sign In</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link btn btn-light text-primary px-3" href="login.php">Sign Up</a>
                </li>
                <?php endif; ?>
            </ul>
        </div>
    </div>
</nav>
