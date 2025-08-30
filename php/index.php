<?php
require_once 'config/config.php';

$auth = new Auth();
$course = new Course();
$user = new User();

// ✅ Use method instead of accessing private property
$categories = $course->getCategories();

// Handle search and filtering
$search = $_GET['search'] ?? '';
$category = $_GET['category'] ?? '';
$page = max(1, intval($_GET['page'] ?? 1));
$limit = 12;
$offset = ($page - 1) * $limit;

// Get courses
$courses = $course->getAll($category, $search, 'published', $limit, $offset);

// Get total count for pagination
$totalCourses = $course->getCourseCount($category);

$totalPages = ceil($totalCourses / $limit);
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= APP_NAME ?> - Learn Online</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="assets/css/style.css" rel="stylesheet">
</head>
<body>
    <?php include 'includes/header.php'; ?>

    <!-- Hero Section -->
    <section class="hero-section bg-primary text-white py-5">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-6">
                    <h1 class="display-4 fw-bold mb-4">Learn New Skills Online</h1>
                    <p class="lead mb-4">Access thousands of courses from top instructors around the world. Start learning today and advance your career.</p>
                    <form class="d-flex" method="GET" action="">
                        <input type="text" name="search" class="form-control form-control-lg me-2" placeholder="Search for courses..." value="<?= htmlspecialchars($search) ?>">
                        <button type="submit" class="btn btn-light btn-lg">Search</button>
                    </form>
                </div>
                <div class="col-lg-6">
                    <img src="assets/images/hero-image.svg" alt="Learning" class="img-fluid">
                </div>
            </div>
        </div>
    </section>

    <!-- Categories Section -->
    <section class="py-5">
        <div class="container">
            <h2 class="text-center mb-5">Popular Categories</h2>
            <div class="row">
                <?php foreach ($categories as $cat): ?>
                <div class="col-md-3 col-sm-6 mb-4">
                    <a href="?category=<?= $cat['id'] ?>" class="text-decoration-none">
                        <div class="card category-card h-100 text-center">
                            <div class="card-body">
                                <i class="fas fa-code fa-3x text-primary mb-3"></i>
                                <h5 class="card-title"><?= htmlspecialchars($cat['name']) ?></h5>
                                <p class="card-text text-muted"><?= htmlspecialchars($cat['description']) ?></p>
                            </div>
                        </div>
                    </a>
                </div>
                <?php endforeach; ?>
            </div>
        </div>
    </section>

    <!-- Courses Section -->
    <section class="py-5 bg-light">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h2>Featured Courses</h2>
                <div class="d-flex gap-2">
                    <select name="category" class="form-select" onchange="window.location.href='?category='+this.value">
                        <option value="">All Categories</option>
                        <?php foreach ($categories as $cat): ?>
                        <option value="<?= $cat['id'] ?>" <?= $category == $cat['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($cat['name']) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            </div>

            <?php if (empty($courses)): ?>
            <div class="text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h4>No courses found</h4>
                <p class="text-muted">Try adjusting your search criteria or browse all categories.</p>
            </div>
            <?php else: ?>
            <div class="row">
                <?php foreach ($courses as $courseItem): ?>
                <div class="col-lg-4 col-md-6 mb-4">
                    <div class="card course-card h-100">
                        <?php if ($courseItem['thumbnail']): ?>
                        <img src="<?= htmlspecialchars($courseItem['thumbnail']) ?>" class="card-img-top" alt="<?= htmlspecialchars($courseItem['title']) ?>">
                        <?php else: ?>
                        <div class="card-img-top bg-secondary d-flex align-items-center justify-content-center" style="height: 200px;">
                            <i class="fas fa-book fa-3x text-white"></i>
                        </div>
                        <?php endif; ?>
                        
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge bg-primary"><?= htmlspecialchars($courseItem['category_name'] ?? 'Uncategorized') ?></span>
                                <span class="badge bg-<?= $courseItem['difficulty_level'] === 'beginner' ? 'success' : ($courseItem['difficulty_level'] === 'intermediate' ? 'warning' : 'danger') ?>">
                                    <?= ucfirst($courseItem['difficulty_level']) ?>
                                </span>
                            </div>
                            
                            <h5 class="card-title">
                                <a href="course.php?slug=<?= $courseItem['slug'] ?>" class="text-decoration-none">
                                    <?= htmlspecialchars($courseItem['title']) ?>
                                </a>
                            </h5>
                            
                            <p class="card-text text-muted">
                                <?= htmlspecialchars(substr($courseItem['short_description'] ?? $courseItem['description'], 0, 100)) ?>...
                            </p>
                            
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">
                                    <i class="fas fa-clock"></i> <?= format_duration($courseItem['duration_hours'] * 60) ?>
                                </small>
                                <small class="text-muted">
                                    <i class="fas fa-user"></i> <?= htmlspecialchars($courseItem['first_name'] . ' ' . $courseItem['last_name']) ?>
                                </small>
                            </div>
                        </div>
                        
                        <div class="card-footer bg-transparent">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="h5 mb-0">
                                    <?= $courseItem['price'] > 0 ? format_price($courseItem['price']) : '<span class="text-success">Free</span>' ?>
                                </span>
                                <a href="course.php?slug=<?= $courseItem['slug'] ?>" class="btn btn-primary btn-sm">
                                    View Course
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                <?php endforeach; ?>
            </div>

            <!-- Pagination -->
            <?php if ($totalPages > 1): ?>
            <nav aria-label="Course pagination">
                <ul class="pagination justify-content-center">
                    <?php for ($i = 1; $i <= $totalPages; $i++): ?>
                    <li class="page-item <?= $i == $page ? 'active' : '' ?>">
                        <a class="page-link" href="?page=<?= $i ?><?= $category ? '&category=' . $category : '' ?>"><?= $i ?></a>
                    </li>
                    <?php endfor; ?>
                </ul>
            </nav>
            <?php endif; ?>
            <?php endif; ?>
        </div>
    </section>

    <!-- Features Section -->
    <section class="py-5">
        <div class="container">
            <h2 class="text-center mb-5">Why Choose Our Platform?</h2>
            <div class="row">
                <div class="col-md-4 text-center mb-4">
                    <i class="fas fa-graduation-cap fa-3x text-primary mb-3"></i>
                    <h4>Expert Instructors</h4>
                    <p class="text-muted">Learn from industry experts and professionals with years of experience.</p>
                </div>
                <div class="col-md-4 text-center mb-4">
                    <i class="fas fa-mobile-alt fa-3x text-primary mb-3"></i>
                    <h4>Learn Anywhere</h4>
                    <p class="text-muted">Access your courses on any device, anytime, anywhere with our mobile-friendly platform.</p>
                </div>
                <div class="col-md-4 text-center mb-4">
                    <i class="fas fa-certificate fa-3x text-primary mb-3"></i>
                    <h4>Get Certified</h4>
                    <p class="text-muted">Earn certificates upon completion to showcase your new skills and knowledge.</p>
                </div>
            </div>
        </div>
    </section>

    <?php include 'includes/footer.php'; ?>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="assets/js/main.js"></script>
</body>
</html>
