class NotificationManager {
    constructor() {
        this.badge = document.getElementById('notificationBadge');
        this.dropdown = document.getElementById('notificationList');
        this.unreadCount = 0;
        this.pollingInterval = null;
        this.isLoading = false;
        
        this.init();
    }
    
    async init() {
        // Wait for DOM to be fully ready
        setTimeout(() => {
            this.setupEventListeners();
            this.loadNotifications();
            this.startPolling();
        }, 500);
    }
    
    setupEventListeners() {
        // Mark all as read button
        const markAllReadBtn = document.getElementById('markAllReadBtn');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.markAllAsRead();
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#notificationDropdown') && 
                !e.target.closest('.dropdown-menu')) {
                const dropdown = document.querySelector('#notificationDropdown + .dropdown-menu');
                if (dropdown && dropdown.classList.contains('show')) {
                    this.loadNotifications(); // Refresh when closing
                }
            }
        });
    }
    
    async loadNotifications() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        try {
            const response = await fetch('/lost_and_found/api/notifications');
            if (!response.ok) throw new Error('Failed to load notifications');
            
            const data = await response.json();
            
            this.unreadCount = data.unread_count;
            this.updateBadge();
            this.renderNotifications(data.notifications);
        } catch (error) {
            console.error('Failed to load notifications:', error);
            this.showErrorState();
        } finally {
            this.isLoading = false;
        }
    }
    
    updateBadge() {
        if (!this.badge) return;
        
        if (this.unreadCount > 0) {
            this.badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            this.badge.style.display = 'block';
            
            // Add animation for new notifications
            if (this.unreadCount > 0) {
                this.badge.classList.add('animate-pulse');
                setTimeout(() => {
                    this.badge.classList.remove('animate-pulse');
                }, 1000);
            }
        } else {
            this.badge.style.display = 'none';
        }
    }
    
    renderNotifications(notifications) {
        if (!this.dropdown) return;
        
        if (!notifications || notifications.length === 0) {
            this.dropdown.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-bell-slash fs-3"></i>
                    <p class="mb-0 mt-2">No notifications</p>
                </div>
            `;
            return;
        }
        
        const items = notifications.map(notif => this.createNotificationItem(notif)).join('');
        this.dropdown.innerHTML = items;
        
        // Add click handlers
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', async (e) => {
                e.preventDefault();
                const notificationId = item.dataset.id;
                const link = item.dataset.link;
                
                // Mark as read
                await this.markAsRead(notificationId);
                
                // Navigate to relevant page if there's a link
                if (link && link !== '#') {
                    window.location.href = link;
                }
                
                // Close dropdown
                const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('notificationDropdown'));
                if (dropdown) dropdown.hide();
            });
        });
    }
    
    createNotificationItem(notification) {
        const timeAgo = this.getTimeAgo(notification.created_at);
        const isReadClass = notification.is_read ? '' : 'fw-bold';
        const readClass = notification.is_read ? '' : 'bg-light';
        
        // Get appropriate icon
        const icon = this.getNotificationIcon(notification.notification_type);
        const link = notification.link || '#';
        
        return `
            <a href="${link}" class="notification-item dropdown-item p-3 border-bottom ${readClass}" 
                 data-id="${notification.id}" 
                 data-link="${link}"
                 style="cursor: pointer; text-decoration: none;">
                <div class="d-flex align-items-start">
                    <div class="flex-shrink-0 me-3">
                        <i class="bi ${icon} fs-5 ${this.getNotificationIconColor(notification.notification_type)}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <p class="mb-1 ${isReadClass}">${notification.message}</p>
                        <small class="text-muted">${timeAgo}</small>
                    </div>
                    ${!notification.is_read ? '<span class="badge bg-primary rounded-pill ms-2">New</span>' : ''}
                </div>
            </a>
        `;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'item_found': 'bi-search',
            'claim_request': 'bi-person-badge',
            'claim_request_anonymous': 'bi-person-badge-fill',
            'claim_accepted': 'bi-check-circle',
            'claim_rejected': 'bi-x-circle',
            'claim_cancelled': 'bi-slash-circle',
            'claim_accepted_confirmation': 'bi-check-circle-fill',
            'item_returned': 'bi-arrow-return-right',
            'item_claimed': 'bi-hand-thumbs-up',
            'item_recovered': 'bi-check-square'
        };
        return icons[type] || 'bi-bell';
    }
    
    getNotificationIconColor(type) {
        const colors = {
            'item_found': 'text-success',
            'claim_request': 'text-primary',
            'claim_request_anonymous': 'text-primary',
            'claim_accepted': 'text-success',
            'claim_rejected': 'text-danger',
            'claim_cancelled': 'text-warning',
            'claim_accepted_confirmation': 'text-success',
            'item_returned': 'text-info',
            'item_claimed': 'text-success',
            'item_recovered': 'text-success'
        };
        return colors[type] || 'text-secondary';
    }
    
    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        let interval = Math.floor(seconds / 31536000);
        if (interval >= 1) {
            return interval + " year" + (interval > 1 ? "s" : "") + " ago";
        }
        interval = Math.floor(seconds / 2592000);
        if (interval >= 1) {
            return interval + " month" + (interval > 1 ? "s" : "") + " ago";
        }
        interval = Math.floor(seconds / 86400);
        if (interval >= 1) {
            return interval + " day" + (interval > 1 ? "s" : "") + " ago";
        }
        interval = Math.floor(seconds / 3600);
        if (interval >= 1) {
            return interval + " hour" + (interval > 1 ? "s" : "") + " ago";
        }
        interval = Math.floor(seconds / 60);
        if (interval >= 1) {
            return interval + " minute" + (interval > 1 ? "s" : "") + " ago";
        }
        return Math.floor(seconds) + " second" + (seconds > 1 ? "s" : "") + " ago";
    }
    
    showErrorState() {
        if (this.dropdown) {
            this.dropdown.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-exclamation-triangle fs-3"></i>
                    <p class="mb-0 mt-2">Failed to load notifications</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="window.notificationManager.loadNotifications()">
                        Retry
                    </button>
                </div>
            `;
        }
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/lost_and_found/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error('Failed to mark notification as read');
            
            const data = await response.json();
            this.unreadCount = data.unread_count;
            this.updateBadge();
            
            // Update the specific notification in the UI
            const notificationItem = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
            if (notificationItem) {
                notificationItem.classList.remove('fw-bold', 'bg-light');
                notificationItem.querySelector('.badge')?.remove();
            }
            
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/lost_and_found/api/notifications/read_all', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error('Failed to mark all notifications as read');
            
            const data = await response.json();
            this.unreadCount = data.unread_count;
            this.updateBadge();
            
            // Update all notifications in the UI
            document.querySelectorAll('.notification-item').forEach(item => {
                item.classList.remove('fw-bold', 'bg-light');
                item.querySelector('.badge')?.remove();
            });
            
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
            alert('Failed to mark all notifications as read');
        }
    }
    
    startPolling() {
        // Poll for new notifications every 30 seconds
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch('/lost_and_found/api/notifications/count');
                if (!response.ok) return;
                
                const data = await response.json();
                if (data.unread_count !== this.unreadCount) {
                    // Only reload if count changed
                    this.unreadCount = data.unread_count;
                    this.updateBadge();
                    
                    // If dropdown is open, refresh the list
                    const dropdown = document.querySelector('#notificationDropdown + .dropdown-menu');
                    if (dropdown && dropdown.classList.contains('show')) {
                        await this.loadNotifications();
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 30000); // 30 seconds
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    
    // Cleanup method
    destroy() {
        this.stopPolling();
    }
}

// CSRF token helper
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if notification dropdown exists
    if (document.getElementById('notificationDropdown')) {
        // Initialize notification manager
        window.notificationManager = new NotificationManager();
        
        // Add some CSS for animations
        const style = document.createElement('style');
        style.textContent = `
            .animate-pulse {
                animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }
            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }
            .notification-item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
        `;
        document.head.appendChild(style);
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (window.notificationManager) {
            window.notificationManager.destroy();
        }
    });
});


// Theme Switching Functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');
    const body = document.body;
    
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('dhallati-theme') || 'light';
    if (savedTheme === 'dark') {
        enableDarkTheme();
    } else {
        enableLightTheme();
    }
    
    // Theme toggle with smooth transition
    themeToggle.addEventListener('click', function() {
        // Prevent multiple clicks during transition
        if (body.classList.contains('theme-transitioning')) return;
        
        body.classList.add('theme-transitioning');
        
        if (body.classList.contains('dark-theme')) {
            enableLightTheme();
        } else {
            enableDarkTheme();
        }
        
        // Button animation
        themeToggle.style.transform = 'scale(1.1) rotate(180deg)';
        setTimeout(() => {
            themeToggle.style.transform = '';
            body.classList.remove('theme-transitioning');
        }, 300);
    });
    
    function enableDarkTheme() {
        body.classList.add('dark-theme');
        themeIcon.className = 'bi bi-sun-fill theme-icon';
        localStorage.setItem('dhallati-theme', 'dark');
        
        // Add subtle transition class to all interactive elements
        document.querySelectorAll('.stat-card, .feature-card, .testimonial-card, .floating-card').forEach(el => {
            el.classList.add('theme-transition');
        });
    }
    
    function enableLightTheme() {
        body.classList.remove('dark-theme');
        themeIcon.className = 'bi bi-moon-fill theme-icon';
        localStorage.setItem('dhallati-theme', 'light');
        
        document.querySelectorAll('.stat-card, .feature-card, .testimonial-card, .floating-card').forEach(el => {
            el.classList.add('theme-transition');
        });
    }
    
    // Smooth scrolling
    document.querySelector('.scroll-indicator').addEventListener('click', () => {
        document.querySelector('#features').scrollIntoView({
            behavior: 'smooth'
        });
    });
    
    // Animate elements on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate__animated', 'animate__fadeInUp');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
    
    // Enhanced count animation
    const counters = document.querySelectorAll('.stat-number');
    
    const startCounting = (entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                counters.forEach(counter => {
                    const target = +counter.getAttribute('data-count');
                    const duration = 2000; // 2 seconds
                    const step = target / (duration / 16); // 60fps
                    let current = 0;
                    
                    const updateCount = () => {
                        current += step;
                        if (current < target) {
                            counter.innerText = Math.floor(current);
                            requestAnimationFrame(updateCount);
                        } else {
                            counter.innerText = target;
                        }
                    };
                    
                    updateCount();
                });
                observer.unobserve(entry.target);
            }
        });
    };
    
    const counterObserver = new IntersectionObserver(startCounting, { threshold: 0.5 });
    const statsContainer = document.querySelector('.stats-container');
    if (statsContainer) counterObserver.observe(statsContainer);
});

// Notification Manager for main page
class NotificationManager {
    constructor() {
        this.badge = document.getElementById('notificationBadge');
        this.dropdown = document.getElementById('notificationList');
        this.unreadCount = 0;
        this.pollingInterval = null;
        this.isLoading = false;
        
        if (this.badge && this.dropdown) {
            this.init();
        }
    }
    
    async init() {
        setTimeout(() => {
            this.setupEventListeners();
            this.loadNotifications();
            this.startPolling();
        }, 500);
    }
    
    setupEventListeners() {
        const markAllReadBtn = document.getElementById('markAllReadBtn');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.markAllAsRead();
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#notificationDropdown') && 
                !e.target.closest('.dropdown-menu')) {
                const dropdown = document.querySelector('#notificationDropdown + .dropdown-menu');
                if (dropdown && dropdown.classList.contains('show')) {
                    this.loadNotifications();
                }
            }
        });
    }
    
    async loadNotifications() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        try {
            const response = await fetch('/lost_and_found/api/notifications');
            if (!response.ok) throw new Error('Failed to load notifications');
            
            const data = await response.json();
            
            this.unreadCount = data.unread_count || 0;
            this.updateBadge();
            this.renderNotifications(data.notifications || []);
        } catch (error) {
            console.error('Failed to load notifications:', error);
            this.showErrorState();
        } finally {
            this.isLoading = false;
        }
    }
    
    updateBadge() {
        if (!this.badge) return;
        
        if (this.unreadCount > 0) {
            this.badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            this.badge.style.display = 'block';
            
            // Add animation for new notifications
            if (this.unreadCount > 0) {
                this.badge.classList.add('animate-pulse');
                setTimeout(() => {
                    this.badge.classList.remove('animate-pulse');
                }, 1000);
            }
        } else {
            this.badge.style.display = 'none';
        }
    }
    
    renderNotifications(notifications) {
        if (!this.dropdown) return;
        
        if (!notifications || notifications.length === 0) {
            this.dropdown.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-bell-slash fs-3"></i>
                    <p class="mb-0 mt-2">No notifications</p>
                </div>
            `;
            return;
        }
        
        const items = notifications.map(notif => this.createNotificationItem(notif)).join('');
        this.dropdown.innerHTML = items;
        
        // Add click handlers
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', async (e) => {
                e.preventDefault();
                const notificationId = item.dataset.id;
                const link = item.dataset.link;
                
                // Mark as read
                await this.markAsRead(notificationId);
                
                // Navigate to relevant page if there's a link
                if (link && link !== '#') {
                    window.location.href = link;
                }
                
                // Close dropdown
                const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('notificationDropdown'));
                if (dropdown) dropdown.hide();
            });
        });
    }
    
    createNotificationItem(notification) {
        const timeAgo = this.getTimeAgo(notification.created_at);
        const isReadClass = notification.is_read ? '' : 'fw-bold';
        const readClass = notification.is_read ? '' : 'bg-light';
        
        // Get appropriate icon
        const icon = this.getNotificationIcon(notification.notification_type);
        const link = notification.link || '#';
        
        // Theme-aware colors
        const iconColor = document.body.classList.contains('dark-theme') 
            ? 'text-warning' 
            : this.getNotificationIconColor(notification.notification_type);
        
        return `
            <a href="${link}" class="notification-item dropdown-item p-3 border-bottom ${readClass}" 
                 data-id="${notification.id}" 
                 data-link="${link}"
                 style="cursor: pointer; text-decoration: none;">
                <div class="d-flex align-items-start">
                    <div class="flex-shrink-0 me-3">
                        <i class="bi ${icon} fs-5 ${iconColor}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <p class="mb-1 ${isReadClass}">${notification.message}</p>
                        <small class="text-muted">${timeAgo}</small>
                    </div>
                    ${!notification.is_read ? '<span class="badge bg-primary rounded-pill ms-2">New</span>' : ''}
                </div>
            </a>
        `;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'item_found': 'bi-search',
            'claim_request': 'bi-person-badge',
            'claim_request_anonymous': 'bi-person-badge-fill',
            'claim_accepted': 'bi-check-circle',
            'claim_rejected': 'bi-x-circle',
            'claim_cancelled': 'bi-slash-circle',
            'claim_accepted_confirmation': 'bi-check-circle-fill',
            'item_returned': 'bi-arrow-return-right',
            'item_claimed': 'bi-hand-thumbs-up',
            'item_recovered': 'bi-check-square'
        };
        return icons[type] || 'bi-bell';
    }
    
    getNotificationIconColor(type) {
        const colors = {
            'item_found': 'text-success',
            'claim_request': 'text-primary',
            'claim_request_anonymous': 'text-primary',
            'claim_accepted': 'text-success',
            'claim_rejected': 'text-danger',
            'claim_cancelled': 'text-warning',
            'claim_accepted_confirmation': 'text-success',
            'item_returned': 'text-info',
            'item_claimed': 'text-success',
            'item_recovered': 'text-success'
        };
        return colors[type] || 'text-secondary';
    }
    
    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return "Just now";
        
        const intervals = {
            year: 31536000,
            month: 2592000,
            day: 86400,
            hour: 3600,
            minute: 60
        };
        
        for (const [unit, secondsInUnit] of Object.entries(intervals)) {
            const interval = Math.floor(seconds / secondsInUnit);
            if (interval >= 1) {
                return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
            }
        }
        
        return "Just now";
    }
    
    showErrorState() {
        if (this.dropdown) {
            this.dropdown.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-exclamation-triangle fs-3"></i>
                    <p class="mb-0 mt-2">Failed to load notifications</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="window.notificationManager.loadNotifications()">
                        Retry
                    </button>
                </div>
            `;
        }
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/lost_and_found/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                this.unreadCount = Math.max(0, this.unreadCount - 1);
                this.updateBadge();
                
                // Update the specific notification in the UI
                const notificationItem = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
                if (notificationItem) {
                    notificationItem.classList.remove('fw-bold', 'bg-light');
                    notificationItem.querySelector('.badge')?.remove();
                }
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/lost_and_found/api/notifications/read_all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                this.unreadCount = 0;
                this.updateBadge();
                
                // Update all notifications in the UI
                document.querySelectorAll('.notification-item').forEach(item => {
                    item.classList.remove('fw-bold', 'bg-light');
                    item.querySelector('.badge')?.remove();
                });
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
            // Show error toast
            showError('Failed to mark all notifications as read');
        }
    }
    
    startPolling() {
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch('/lost_and_found/api/notifications/count');
                if (!response.ok) return;
                
                const data = await response.json();
                if (data.unread_count !== this.unreadCount) {
                    this.unreadCount = data.unread_count;
                    this.updateBadge();
                    
                    // If dropdown is open, refresh the list
                    const dropdown = document.querySelector('#notificationDropdown + .dropdown-menu');
                    if (dropdown && dropdown.classList.contains('show')) {
                        await this.loadNotifications();
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 30000); // 30 seconds
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    
    destroy() {
        this.stopPolling();
    }
}

// Initialize notification manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize notification manager if notification dropdown exists
    if (document.getElementById('notificationDropdown')) {
        window.notificationManager = new NotificationManager();
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (window.notificationManager) {
            window.notificationManager.destroy();
        }
    });
    
    // Setup intersection observer for scroll animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
});