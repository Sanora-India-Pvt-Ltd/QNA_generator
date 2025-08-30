<footer class="bg-dark text-light py-5 mt-5">
    <div class="container">
        <div class="row">
            <div class="col-md-4 mb-4">
                <h5 class="mb-3"><?= APP_NAME ?></h5>
                <p class="text-muted">Empowering learners worldwide with quality education and professional development opportunities.</p>
                <div class="social-links">
                    <a href="#" class="text-light me-3"><i class="fab fa-facebook-f"></i></a>
                    <a href="#" class="text-light me-3"><i class="fab fa-twitter"></i></a>
                    <a href="#" class="text-light me-3"><i class="fab fa-linkedin-in"></i></a>
                    <a href="#" class="text-light"><i class="fab fa-instagram"></i></a>
                </div>
            </div>
            
            <div class="col-md-2 mb-4">
                <h6 class="mb-3">Platform</h6>
                <ul class="list-unstyled">
                    <li><a href="courses.php" class="text-muted text-decoration-none">Browse Courses</a></li>
                    <li><a href="about.php" class="text-muted text-decoration-none">About Us</a></li>
                    <li><a href="contact.php" class="text-muted text-decoration-none">Contact</a></li>
                    <li><a href="faq.php" class="text-muted text-decoration-none">FAQ</a></li>
                </ul>
            </div>
            
            <div class="col-md-2 mb-4">
                <h6 class="mb-3">Support</h6>
                <ul class="list-unstyled">
                    <li><a href="help.php" class="text-muted text-decoration-none">Help Center</a></li>
                    <li><a href="privacy.php" class="text-muted text-decoration-none">Privacy Policy</a></li>
                    <li><a href="terms.php" class="text-muted text-decoration-none">Terms of Service</a></li>
                    <li><a href="support.php" class="text-muted text-decoration-none">Support</a></li>
                </ul>
            </div>
            
            <div class="col-md-4 mb-4">
                <h6 class="mb-3">Newsletter</h6>
                <p class="text-muted">Stay updated with our latest courses and offers.</p>
                <form class="d-flex">
                    <input type="email" class="form-control me-2" placeholder="Enter your email">
                    <button type="submit" class="btn btn-primary">Subscribe</button>
                </form>
            </div>
        </div>
        
        <hr class="my-4">
        
        <div class="row align-items-center">
            <div class="col-md-6">
                <p class="mb-0 text-muted">&copy; <?= date('Y') ?> <?= APP_NAME ?>. All rights reserved.</p>
            </div>
            <div class="col-md-6 text-md-end">
                <p class="mb-0 text-muted">Made with <i class="fas fa-heart text-danger"></i> for education</p>
            </div>
        </div>
    </div>
</footer>
