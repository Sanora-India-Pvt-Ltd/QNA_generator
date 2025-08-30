<?php
require_once 'config/config.php';

$auth = new Auth();
$auth->requireAuth();

$user = new User();
$course = new Course();
$currentUser = $auth->getCurrentUser();

// Get user statistics
$stats = $user->getStats($currentUser['id']);

// Get enrolled courses
$enrolledCourses = $user->getEnrolledCourses($currentUser['id']);

// Get recent activity (last 5 lessons completed)
$recentActivity = $user->db->fetchAll(
    "SELECT lp.*, l.title as lesson_title, c.title as course_title, c.slug as course_slug
     FROM lesson_progress lp
     JOIN lessons l ON lp.lesson_id = l.id
     JOIN courses c ON l.course_id = c.id
     WHERE lp.student_id = ? AND lp.is_completed = 1
     ORDER BY lp.completed_at DESC
     LIMIT 5",
    [$currentUser['id']]
);

// Get recommended courses
$recommendedCourses = $course->getAll(null, null, 'published', 6);
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="assets/css/style.css" rel="stylesheet">
</head>
<body>
    <?php include 'includes/header.php'; ?>

    <div class="container py-5">
        <!-- Welcome Section -->
        <div class="row mb-5">
            <div class="col-12">
                <h1 class="display-6 fw-bold">Welcome back, <?= htmlspecialchars($currentUser['first_name']) ?>!</h1>
                <p class="text-muted">Continue your learning journey and track your progress.</p>
            </div>
        </div>

        <!-- Statistics Cards -->
        <div class="row mb-5">
            <div class="col-md-3 col-sm-6 mb-4">
                <div class="card bg-primary text-white h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4 class="mb-0"><?= $stats['enrolled_courses'] ?></h4>
                                <p class="mb-0">Enrolled Courses</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-book fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 col-sm-6 mb-4">
                <div class="card bg-success text-white h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4 class="mb-0"><?= $stats['completed_courses'] ?></h4>
                                <p class="mb-0">Completed Courses</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-check-circle fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 col-sm-6 mb-4">
                <div class="card bg-info text-white h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4 class="mb-0"><?= $stats['completed_lessons'] ?></h4>
                                <p class="mb-0">Lessons Completed</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-play-circle fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 col-sm-6 mb-4">
                <div class="card bg-warning text-white h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4 class="mb-0"><?= round($stats['avg_quiz_score'], 1) ?>%</h4>
                                <p class="mb-0">Avg Quiz Score</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-chart-line fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Enrolled Courses -->
            <div class="col-lg-8 mb-5">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">My Courses</h5>
                    </div>
                    <div class="card-body">
                        <?php if (empty($enrolledCourses)): ?>
                        <div class="text-center py-4">
                            <i class="fas fa-book-open fa-3x text-muted mb-3"></i>
                            <h5>No courses enrolled yet</h5>
                            <p class="text-muted">Start your learning journey by enrolling in a course.</p>
                            <a href="courses.php" class="btn btn-primary">Browse Courses</a>
                        </div>
                        <?php else: ?>
                        <div class="row">
                            <?php foreach ($enrolledCourses as $enrolledCourse): ?>
                            <div class="col-md-6 mb-4">
                                <div class="card h-100">
                                    <?php if ($enrolledCourse['thumbnail']): ?>
                                    <img src="<?= htmlspecialchars($enrolledCourse['thumbnail']) ?>" class="card-img-top" alt="<?= htmlspecialchars($enrolledCourse['title']) ?>">
                                    <?php else: ?>
                                    <div class="card-img-top bg-secondary d-flex align-items-center justify-content-center" style="height: 150px;">
                                        <i class="fas fa-book fa-2x text-white"></i>
                                    </div>
                                    <?php endif; ?>
                                    
                                    <div class="card-body">
                                        <h6 class="card-title"><?= htmlspecialchars($enrolledCourse['title']) ?></h6>
                                        <div class="mb-3">
                                            <div class="d-flex justify-content-between mb-1">
                                                <small class="text-muted">Progress</small>
                                                <small class="text-muted"><?= $enrolledCourse['progress_percentage'] ?>%</small>
                                            </div>
                                            <div class="progress" style="height: 6px;">
                                                <div class="progress-bar" style="width: <?= $enrolledCourse['progress_percentage'] ?>%"></div>
                                            </div>
                                        </div>
                                        <a href="course.php?slug=<?= $enrolledCourse['slug'] ?>" class="btn btn-primary btn-sm">Continue Learning</a>
                                    </div>
                                </div>
                            </div>
                            <?php endforeach; ?>
                        </div>
                        <?php endif; ?>
                    </div>
                </div>
            </div>

            <!-- Sidebar -->
            <div class="col-lg-4">
                <!-- Recent Activity -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">Recent Activity</h6>
                    </div>
                    <div class="card-body">
                        <?php if (empty($recentActivity)): ?>
                        <p class="text-muted text-center">No recent activity</p>
                        <?php else: ?>
                        <div class="timeline">
                            <?php foreach ($recentActivity as $activity): ?>
                            <div class="timeline-item mb-3">
                                <div class="d-flex">
                                    <div class="timeline-marker bg-success rounded-circle me-3" style="width: 10px; height: 10px; margin-top: 5px;"></div>
                                    <div>
                                        <small class="text-muted"><?= date('M j, Y', strtotime($activity['completed_at'])) ?></small>
                                        <p class="mb-1 small">Completed: <?= htmlspecialchars($activity['lesson_title']) ?></p>
                                        <small class="text-muted"><?= htmlspecialchars($activity['course_title']) ?></small>
                                    </div>
                                </div>
                            </div>
                            <?php endforeach; ?>
                        </div>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">Quick Actions</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <a href="courses.php" class="btn btn-outline-primary btn-sm">
                                <i class="fas fa-search me-2"></i>Browse Courses
                            </a>
                            <a href="profile.php" class="btn btn-outline-secondary btn-sm">
                                <i class="fas fa-user me-2"></i>Edit Profile
                            </a>
                            <a href="certificates.php" class="btn btn-outline-success btn-sm">
                                <i class="fas fa-certificate me-2"></i>View Certificates
                            </a>
                        </div>
                    </div>
                </div>

                <!-- Recommended Courses -->
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Recommended for You</h6>
                    </div>
                    <div class="card-body">
                        <?php foreach (array_slice($recommendedCourses, 0, 3) as $recCourse): ?>
                        <div class="d-flex mb-3">
                            <div class="flex-shrink-0">
                                <div class="bg-secondary rounded" style="width: 50px; height: 50px; display: flex; align-items: center; justify-content: center;">
                                    <i class="fas fa-book text-white"></i>
                                </div>
                            </div>
                            <div class="flex-grow-1 ms-3">
                                <h6 class="mb-1 small"><?= htmlspecialchars($recCourse['title']) ?></h6>
                                <small class="text-muted"><?= htmlspecialchars($recCourse['first_name'] . ' ' . $recCourse['last_name']) ?></small>
                                <br>
                                <small class="text-primary"><?= $recCourse['price'] > 0 ? format_price($recCourse['price']) : 'Free' ?></small>
                            </div>
                        </div>
                        <?php endforeach; ?>
                        <a href="courses.php" class="btn btn-link btn-sm p-0">View all recommendations →</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <?php include 'includes/footer.php'; ?>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="assets/js/main.js"></script>
</body>
</html>
