// Main JavaScript file for Learning Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Course search functionality
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const courseCards = document.querySelectorAll('.course-card');
            
            courseCards.forEach(card => {
                const title = card.querySelector('.card-title').textContent.toLowerCase();
                const description = card.querySelector('.card-text').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || description.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Progress bar animation
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
        }, 500);
    });

    // Quiz functionality
    const quizOptions = document.querySelectorAll('.quiz-option');
    quizOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from other options in the same question
            const question = this.closest('.quiz-question');
            question.querySelectorAll('.quiz-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update hidden input if it exists
            const questionId = this.getAttribute('data-question-id');
            const answerId = this.getAttribute('data-answer-id');
            const hiddenInput = document.querySelector(`input[name="answer[${questionId}]"]`);
            if (hiddenInput) {
                hiddenInput.value = answerId;
            }
        });
    });

    // Lesson completion tracking
    const completeButtons = document.querySelectorAll('.complete-lesson');
    completeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const lessonId = this.getAttribute('data-lesson-id');
            const button = this;
            
            // Show loading state
            button.innerHTML = '<span class="loading"></span> Completing...';
            button.disabled = true;
            
            // Send AJAX request to mark lesson as complete
            fetch('/api/complete-lesson.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    lesson_id: lessonId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    button.innerHTML = '<i class="fas fa-check"></i> Completed';
                    button.classList.remove('btn-primary');
                    button.classList.add('btn-success');
                    
                    // Update progress bar if it exists
                    const progressBar = document.querySelector('.course-progress .progress-bar');
                    if (progressBar) {
                        const currentProgress = parseInt(progressBar.style.width);
                        const newProgress = Math.min(currentProgress + 10, 100);
                        progressBar.style.width = newProgress + '%';
                        progressBar.textContent = newProgress + '%';
                    }
                    
                    showToast('Lesson completed successfully!', 'success');
                } else {
                    button.innerHTML = '<i class="fas fa-play"></i> Complete Lesson';
                    button.disabled = false;
                    showToast('Failed to complete lesson. Please try again.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.innerHTML = '<i class="fas fa-play"></i> Complete Lesson';
                button.disabled = false;
                showToast('An error occurred. Please try again.', 'error');
            });
        });
    });

    // Video player functionality
    const videoPlayers = document.querySelectorAll('.video-player');
    videoPlayers.forEach(player => {
        const video = player.querySelector('video');
        const playButton = player.querySelector('.play-button');
        const progressBar = player.querySelector('.progress-bar');
        const timeDisplay = player.querySelector('.time-display');
        
        if (video && playButton) {
            playButton.addEventListener('click', function() {
                if (video.paused) {
                    video.play();
                    playButton.innerHTML = '<i class="fas fa-pause"></i>';
                } else {
                    video.pause();
                    playButton.innerHTML = '<i class="fas fa-play"></i>';
                }
            });
            
            // Update progress bar
            video.addEventListener('timeupdate', function() {
                const progress = (video.currentTime / video.duration) * 100;
                progressBar.style.width = progress + '%';
                
                // Update time display
                const currentTime = formatTime(video.currentTime);
                const duration = formatTime(video.duration);
                timeDisplay.textContent = `${currentTime} / ${duration}`;
            });
            
            // Track video progress
            video.addEventListener('ended', function() {
                // Auto-complete lesson when video ends
                const completeButton = document.querySelector('.complete-lesson');
                if (completeButton) {
                    completeButton.click();
                }
            });
        }
    });

    // Payment form validation
    const paymentForm = document.querySelector('#payment-form');
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(e) {
            const cardNumber = document.querySelector('#card-number').value;
            const expiryDate = document.querySelector('#expiry-date').value;
            const cvv = document.querySelector('#cvv').value;
            
            if (!cardNumber || !expiryDate || !cvv) {
                e.preventDefault();
                showToast('Please fill in all payment fields.', 'error');
                return false;
            }
            
            // Basic card number validation
            if (cardNumber.replace(/\s/g, '').length < 13) {
                e.preventDefault();
                showToast('Please enter a valid card number.', 'error');
                return false;
            }
        });
    }

    // Certificate download
    const downloadButtons = document.querySelectorAll('.download-certificate');
    downloadButtons.forEach(button => {
        button.addEventListener('click', function() {
            const certificateId = this.getAttribute('data-certificate-id');
            
            // Show loading state
            button.innerHTML = '<span class="loading"></span> Generating...';
            button.disabled = true;
            
            // Generate and download certificate
            fetch(`/api/generate-certificate.php?id=${certificateId}`)
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `certificate-${certificateId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                button.innerHTML = '<i class="fas fa-download"></i> Download';
                button.disabled = false;
                showToast('Certificate downloaded successfully!', 'success');
            })
            .catch(error => {
                console.error('Error:', error);
                button.innerHTML = '<i class="fas fa-download"></i> Download';
                button.disabled = false;
                showToast('Failed to download certificate.', 'error');
            });
        });
    });

    // Auto-save form data
    const forms = document.querySelectorAll('form[data-autosave]');
    forms.forEach(form => {
        const formId = form.getAttribute('data-autosave');
        const inputs = form.querySelectorAll('input, textarea, select');
        
        // Load saved data
        inputs.forEach(input => {
            const savedValue = localStorage.getItem(`${formId}_${input.name}`);
            if (savedValue) {
                input.value = savedValue;
            }
        });
        
        // Save data on input change
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                localStorage.setItem(`${formId}_${this.name}`, this.value);
            });
        });
        
        // Clear saved data on form submit
        form.addEventListener('submit', function() {
            inputs.forEach(input => {
                localStorage.removeItem(`${formId}_${input.name}`);
            });
        });
    });

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Lazy loading for images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
});

// Utility functions
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to toast container
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for use in other scripts
window.LMS = {
    showToast,
    formatTime,
    debounce
};
