<?php
require_once 'config/config.php';

$auth = new Auth();
$course = new Course();
$user = new User();
$payment = new Payment();

$slug = $_GET['slug'] ?? '';
if (empty($slug)) {
    redirect('/courses.php');
}

$courseData = $course->getBySlug($slug);
if (!$courseData) {
    redirect('/courses.php');
}

$currentUser = $auth->getCurrentUser();
$isEnrolled = $currentUser ? $course->isEnrolled($courseData['id'], $currentUser['id']) : false;
$lessons = $course->getLessons($courseData['id']);
$quizzes = $course->getQuizzes($courseData['id']);
$enrollmentCount = $course->getEnrollmentCount($courseData['id']);

// Handle enrollment
if ($_POST && isset($_POST['enroll']) && $currentUser) {
    if ($courseData['price'] > 0) {
        // Redirect to payment
        redirect("/payment.php?course_id=" . $courseData['id']);
    } else {
        // Free course - enroll directly
        $result = $course->enroll($courseData['id'], $currentUser['id']);
        if ($result['success']) {
            redirect("/course.php?slug=" . $slug);
        }
    }
}

// Get progress if enrolled
$progress = null;
if ($isEnrolled && $currentUser) {
    $progress = $course->getProgress($courseData['id'], $currentUser['id']);
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($courseData['title']) ?> - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="assets/css/style.css" rel="stylesheet">
</head>
<body>
    <?php include 'includes/header.php'; ?>

    <div class="container py-5">
        <div class="row">
            <!-- Course Content -->
            <div class="col-lg-8">
                <!-- Course Header -->
                <div class="mb-4">
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="courses.php">Courses</a></li>
                            <li class="breadcrumb-item active"><?= htmlspecialchars($courseData['title']) ?></li>
                        </ol>
                    </nav>
                    
                    <?php if ($courseData['thumbnail']): ?>
                    <img src="<?= htmlspecialchars($courseData['thumbnail']) ?>" class="img-fluid rounded mb-3" alt="<?= htmlspecialchars($courseData['title']) ?>">
                    <?php endif; ?>
                    
                    <h1 class="display-5 fw-bold"><?= htmlspecialchars($courseData['title']) ?></h1>
                    <p class="lead text-muted"><?= htmlspecialchars($courseData['short_description'] ?? $courseData['description']) ?></p>
                    
                    <div class="d-flex align-items-center mb-3">
                        <div class="d-flex align-items-center me-4">
                            <i class="fas fa-user text-muted me-2"></i>
                            <span class="text-muted"><?= htmlspecialchars($courseData['first_name'] . ' ' . $courseData['last_name']) ?></span>
                        </div>
                        <div class="d-flex align-items-center me-4">
                            <i class="fas fa-users text-muted me-2"></i>
                            <span class="text-muted"><?= $enrollmentCount ?> students enrolled</span>
                        </div>
                        <div class="d-flex align-items-center">
                            <i class="fas fa-clock text-muted me-2"></i>
                            <span class="text-muted"><?= format_duration($courseData['duration_hours'] * 60) ?></span>
                        </div>
                    </div>
                    
                    <div class="d-flex align-items-center mb-4">
                        <span class="badge bg-primary me-2"><?= htmlspecialchars($courseData['category_name'] ?? 'Uncategorized') ?></span>
                        <span class="badge bg-<?= $courseData['difficulty_level'] === 'beginner' ? 'success' : ($courseData['difficulty_level'] === 'intermediate' ? 'warning' : 'danger') ?>">
                            <?= ucfirst($courseData['difficulty_level']) ?>
                        </span>
                    </div>
                </div>

                <!-- Course Description -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="mb-0">About This Course</h5>
                    </div>
                    <div class="card-body">
                        <div class="course-description">
                            <?= nl2br(htmlspecialchars($courseData['description'])) ?>
                        </div>
                    </div>
                </div>

                <!-- Course Content -->
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Course Content</h5>
                        <?php if ($isEnrolled && $progress): ?>
                        <span class="badge bg-success"><?= $progress['completed_lessons'] ?> of <?= $progress['total_lessons'] ?> lessons completed</span>
                        <?php endif; ?>
                    </div>
                    <div class="card-body">
                        <?php if (empty($lessons)): ?>
                        <p class="text-muted text-center py-3">No lessons available yet.</p>
                        <?php else: ?>
                        <div class="accordion" id="lessonsAccordion">
                            <?php foreach ($lessons as $index => $lesson): ?>
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="lesson<?= $lesson['id'] ?>">
                                    <button class="accordion-button <?= $index > 0 ? 'collapsed' : '' ?>" type="button" data-bs-toggle="collapse" data-bs-target="#collapse<?= $lesson['id'] ?>">
                                        <div class="d-flex align-items-center w-100">
                                            <span class="me-3"><?= $index + 1 ?></span>
                                            <span class="flex-grow-1"><?= htmlspecialchars($lesson['title']) ?></span>
                                            <span class="text-muted me-2"><?= format_duration($lesson['duration_minutes']) ?></span>
                                            <?php if ($isEnrolled): ?>
                                                <?php 
                                                $lessonObj = new Lesson();
                                                $isCompleted = $lessonObj->isCompleted($lesson['id'], $currentUser['id']);
                                                ?>
                                                <?php if ($isCompleted): ?>
                                                <i class="fas fa-check-circle text-success"></i>
                                                <?php else: ?>
                                                <i class="fas fa-circle text-muted"></i>
                                                <?php endif; ?>
                                            <?php else: ?>
                                                <?php if ($lesson['is_free']): ?>
                                                <span class="badge bg-success">Free</span>
                                                <?php else: ?>
                                                <i class="fas fa-lock text-muted"></i>
                                                <?php endif; ?>
                                            <?php endif; ?>
                                        </div>
                                    </button>
                                </h2>
                                <div id="collapse<?= $lesson['id'] ?>" class="accordion-collapse collapse <?= $index === 0 ? 'show' : '' ?>" data-bs-parent="#lessonsAccordion">
                                    <div class="accordion-body">
                                        <p class="text-muted"><?= htmlspecialchars(substr($lesson['content'] ?? '', 0, 200)) ?>...</p>
                                        <?php if ($isEnrolled || $lesson['is_free']): ?>
                                        <a href="lesson.php?id=<?= $lesson['id'] ?>" class="btn btn-primary btn-sm">Start Lesson</a>
                                        <?php else: ?>
                                        <span class="text-muted">Enroll to access this lesson</span>
                                        <?php endif; ?>
                                    </div>
                                </div>
                            </div>
                            <?php endforeach; ?>
                        </div>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- Quizzes -->
                <?php if (!empty($quizzes)): ?>
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="mb-0">Quizzes & Assessments</h5>
                    </div>
                    <div class="card-body">
                        <?php foreach ($quizzes as $quiz): ?>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h6 class="mb-1"><?= htmlspecialchars($quiz['title']) ?></h6>
                                <small class="text-muted"><?= htmlspecialchars($quiz['description']) ?></small>
                            </div>
                            <div class="text-end">
                                <small class="text-muted d-block"><?= $quiz['time_limit_minutes'] ?> minutes</small>
                                <?php if ($isEnrolled): ?>
                                <a href="quiz.php?id=<?= $quiz['id'] ?>" class="btn btn-outline-primary btn-sm">Take Quiz</a>
                                <?php else: ?>
                                <span class="text-muted">Enroll to take quiz</span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <?php endforeach; ?>
                    </div>
                </div>
                <?php endif; ?>
            </div>

            <!-- Sidebar -->
            <div class="col-lg-4">
                <!-- Enrollment Card -->
                <div class="card sticky-top" style="top: 20px;">
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h3 class="mb-0">
                                <?= $courseData['price'] > 0 ? format_price($courseData['price']) : '<span class="text-success">Free</span>' ?>
                            </h3>
                            <?php if ($courseData['price'] > 0): ?>
                            <small class="text-muted">One-time payment</small>
                            <?php endif; ?>
                        </div>

                        <?php if ($isEnrolled): ?>
                        <div class="d-grid gap-2">
                            <a href="lesson.php?course_id=<?= $courseData['id'] ?>" class="btn btn-success">
                                <i class="fas fa-play me-2"></i>Continue Learning
                            </a>
                            <?php if ($progress): ?>
                            <div class="progress mb-2" style="height: 8px;">
                                <div class="progress-bar" style="width: <?= $progress['progress_percentage'] ?>%"></div>
                            </div>
                            <small class="text-muted text-center d-block"><?= $progress['progress_percentage'] ?>% Complete</small>
                            <?php endif; ?>
                        </div>
                        <?php else: ?>
                        <div class="d-grid gap-2">
                            <?php if ($auth->isLoggedIn()): ?>
                            <form method="POST">
                                <button type="submit" name="enroll" class="btn btn-primary btn-lg">
                                    <i class="fas fa-graduation-cap me-2"></i>
                                    <?= $courseData['price'] > 0 ? 'Enroll Now' : 'Enroll for Free' ?>
                                </button>
                            </form>
                            <?php else: ?>
                            <a href="login.php" class="btn btn-primary btn-lg">
                                <i class="fas fa-sign-in-alt me-2"></i>Sign in to Enroll
                            </a>
                            <?php endif; ?>
                        </div>
                        <?php endif; ?>

                        <hr>

                        <div class="row text-center">
                            <div class="col-4">
                                <div class="border-end">
                                    <h6 class="mb-1"><?= count($lessons) ?></h6>
                                    <small class="text-muted">Lessons</small>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="border-end">
                                    <h6 class="mb-1"><?= $courseData['duration_hours'] ?></h6>
                                    <small class="text-muted">Hours</small>
                                </div>
                            </div>
                            <div class="col-4">
                                <h6 class="mb-1"><?= count($quizzes) ?></h6>
                                <small class="text-muted">Quizzes</small>
                            </div>
                        </div>

                        <hr>

                        <div class="d-flex align-items-center mb-2">
                            <i class="fas fa-shield-alt text-success me-2"></i>
                            <small class="text-muted">30-Day Money-Back Guarantee</small>
                        </div>
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas fa-certificate text-primary me-2"></i>
                            <small class="text-muted">Certificate of Completion</small>
                        </div>
                        <div class="d-flex align-items-center">
                            <i class="fas fa-infinity text-info me-2"></i>
                            <small class="text-muted">Lifetime Access</small>
                        </div>
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
