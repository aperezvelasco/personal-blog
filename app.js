/**
 * App.js
 * Personal Portfolio & Geoscience Blog Interactivity
 * Antonio Pérez Velasco (pereza)
 */

document.addEventListener("DOMContentLoaded", () => {
    // State management
    let postsData = [];
    let currentFilter = "all";
    let searchQuery = "";

    // DOM Elements
    const blogFeed = document.getElementById("blog-feed");
    const searchInput = document.getElementById("search-input");
    const filterButtons = document.querySelectorAll(".filter-btn");
    const themeToggleBtn = document.getElementById("theme-toggle");
    const mobileMenuToggle = document.querySelector(".mobile-nav-toggle");
    const mobileDrawer = document.querySelector(".mobile-drawer");
    const navLinks = document.querySelectorAll(".nav-link, .mobile-link");
    
    // Modal Elements
    const postModal = document.getElementById("post-modal");
    const modalBody = document.getElementById("modal-body");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    const modalOverlay = document.querySelector(".modal-overlay");

    // Initialize Page
    initTheme();
    loadBlogData();
    setupEventListeners();
    setupScrollSpy();
    initStormBackground();

    /**
     * Fetch the compiled posts and papers from JSON data file
     */
    async function loadBlogData() {
        try {
            const response = await fetch("data/posts.json");
            if (!response.ok) {
                throw new Error("Failed to load blog posts data.");
            }
            postsData = await response.json();
            renderFeed();
        } catch (error) {
            console.error("Error loading blog feed:", error);
            blogFeed.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--accent-blue);"></i>
                    <p>Failed to load literature feed. Please try again later or verify data/posts.json exists.</p>
                </div>
            `;
        }
    }

    /**
     * Map filter buttons to categories in posts data
     */
    function getFilterKey(filterName) {
        const mapping = {
            "blog": "Blog",
            "weather": "Weather Forecasting",
            "s2s": "Subseasonal to Seasonal Forecasting",
            "emulation": "Climate Emulation",
            "assimilation": "Data Assimilation",
            "downscaling": "Downscaling"
        };
        return mapping[filterName] || "all";
    }

    /**
     * Render feed card elements dynamically with animation delays
     */
    function renderFeed() {
        blogFeed.innerHTML = "";
        
        // Filter and Search logic
        const filteredPosts = postsData.filter(post => {
            // Category filter
            const filterKey = getFilterKey(currentFilter);
            const matchesCategory = filterKey === "all" || post.category === filterKey;
            
            // Search query filter
            const searchLower = searchQuery.toLowerCase();
            const matchesSearch = searchQuery === "" || 
                post.title.toLowerCase().includes(searchLower) ||
                post.summary.toLowerCase().includes(searchLower) ||
                (post.full_content && post.full_content.toLowerCase().includes(searchLower)) ||
                post.authors.some(author => author.toLowerCase().includes(searchLower));
                
            return matchesCategory && matchesSearch;
        });

        if (filteredPosts.length === 0) {
            blogFeed.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-magnifying-glass" style="font-size: 2rem;"></i>
                    <p>No posts or papers found matching your criteria.</p>
                </div>
            `;
            return;
        }

        filteredPosts.forEach((post, index) => {
            const card = document.createElement("div");
            card.classList.add("feed-card");
            card.setAttribute("data-id", post.id);
            
            // Setup responsive mouse movement variables for glow effect
            card.addEventListener("mousemove", (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                card.style.setProperty("--mouse-x", `${x}px`);
                card.style.setProperty("--mouse-y", `${y}px`);
            });

            const isBlog = post.type === "blog";
            const tagClass = isBlog ? "tag-blog" : "tag-paper";
            const tagLabel = isBlog ? "Blog Post" : post.category;
            
            // Clean authors display
            let authorsList = "Antonio Pérez Velasco";
            if (post.authors && post.authors.length > 0) {
                if (post.authors.length > 3) {
                    authorsList = post.authors.slice(0, 3).join(", ") + " et al.";
                } else {
                    authorsList = post.authors.join(", ");
                }
            }

            card.innerHTML = `
                <div class="card-header-meta">
                    <span class="card-tag ${tagClass}">${tagLabel}</span>
                    <span class="card-date">${post.date}</span>
                </div>
                <h3 class="card-title">${post.title}</h3>
                <p class="card-summary">${post.summary}</p>
                <div class="card-footer">
                    <span class="card-authors" title="${post.authors ? post.authors.join(', ') : ''}">
                        <i class="fa-solid fa-user-pen"></i> ${authorsList}
                    </span>
                    <span class="card-more">Read More <i class="fa-solid fa-arrow-right"></i></span>
                </div>
            `;

            // Open modal on click
            card.addEventListener("click", () => openModal(post));
            
            blogFeed.appendChild(card);
        });
    }

    /**
     * Modal logic
     */
    function openModal(post) {
        const isBlog = post.type === "blog";
        const authorsList = post.authors ? post.authors.join(", ") : "Antonio Pérez Velasco";
        
        let footerBtn = "";
        if (post.link) {
            const btnText = isBlog ? "Read Full Article" : "View on arXiv <i class='fa-solid fa-arrow-up-right-from-square'></i>";
            footerBtn = `<a href="${post.link}" target="_blank" rel="noopener" class="btn btn-primary">${btnText}</a>`;
        }

        modalBody.innerHTML = `
            <div class="modal-header">
                <div class="modal-category-date">
                    <span class="modal-tag">${post.category}</span>
                    <span>&bull;</span>
                    <span>Published: ${post.date}</span>
                </div>
                <h2 class="modal-title">${post.title}</h2>
                <div class="modal-authors">
                    <i class="fa-solid fa-user-group"></i> ${authorsList}
                </div>
            </div>
            <div class="modal-body-content">
                ${isBlog ? post.full_content : `<p>${post.full_content}</p>`}
            </div>
            <div class="modal-footer">
                ${footerBtn}
            </div>
        `;

        postModal.classList.add("open");
        postModal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden"; // Prevent background scroll
    }

    function closeModal() {
        postModal.classList.remove("open");
        postModal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = ""; // Re-enable scroll
    }

    /**
     * Event Listeners setup
     */
    function setupEventListeners() {
        // Search Input
        searchInput.addEventListener("input", (e) => {
            searchQuery = e.target.value;
            renderFeed();
        });

        // Filter Tabs
        filterButtons.forEach(button => {
            button.addEventListener("click", () => {
                filterButtons.forEach(btn => btn.classList.remove("active"));
                button.classList.add("active");
                currentFilter = button.getAttribute("data-filter");
                renderFeed();
            });
        });

        // Modal Close handlers
        modalCloseBtn.addEventListener("click", closeModal);
        modalOverlay.addEventListener("click", closeModal);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && postModal.classList.contains("open")) {
                closeModal();
            }
        });

        // Theme Toggle
        themeToggleBtn.addEventListener("click", toggleTheme);

        // Mobile Nav Drawer Toggle
        mobileMenuToggle.addEventListener("click", () => {
            const isOpen = mobileDrawer.classList.contains("open");
            if (isOpen) {
                mobileDrawer.classList.remove("open");
                mobileMenuToggle.innerHTML = '<i class="fa-solid fa-bars"></i>';
            } else {
                mobileDrawer.classList.add("open");
                mobileMenuToggle.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            }
        });

        // Close mobile drawer on navigation click
        navLinks.forEach(link => {
            link.addEventListener("click", () => {
                mobileDrawer.classList.remove("open");
                mobileMenuToggle.innerHTML = '<i class="fa-solid fa-bars"></i>';
            });
        });
    }

    /**
     * Light/Dark Theme management
     */
    function initTheme() {
        const savedTheme = localStorage.getItem("theme");
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        
        if (savedTheme === "light") {
            setTheme("light");
        } else if (savedTheme === "dark") {
            setTheme("dark");
        } else {
            setTheme(prefersDark ? "dark" : "light");
        }
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        setTheme(newTheme);
    }

    function setTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
        
        // Update Toggle Button Icon
        if (theme === "dark") {
            themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
        } else {
            themeToggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
        }
    }

    /**
     * Active link highlight on scroll (Intersection Observer)
     */
    function setupScrollSpy() {
        const sections = document.querySelectorAll("section");
        const navItems = document.querySelectorAll(".nav-link");

        const options = {
            root: null,
            rootMargin: "0px",
            threshold: 0.3
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.getAttribute("id");
                    navItems.forEach(item => {
                        item.classList.remove("active");
                        if (item.getAttribute("href") === `#${id}`) {
                            item.classList.add("active");
                        }
                    });
                }
            });
        }, options);

        sections.forEach(section => observer.observe(section));
    }

    /**
     * Interactive Storm Background Canvas animation
     */
    function initStormBackground() {
        const canvas = document.getElementById("storm-canvas");
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;
        
        const particles = [];
        const particleCount = 100;
        const maxSpeed = 3.5;
        const historyLimit = 22; // Longer history for a smooth, natural trail
        
        // Vortexes: 2 ambient storm eddies + 1 mouse interactive storm eddy
        const vortexes = [
            { x: width * 0.25, y: height * 0.35, radius: 280, attraction: 0.05, rotation: 1.2 },
            { x: width * 0.75, y: height * 0.65, radius: 320, attraction: 0.04, rotation: 0.9 },
            { x: -1000, y: -1000, radius: 250, attraction: 0.12, rotation: 2.0 } // Mouse vortex
        ];
        const mouseVortex = vortexes[2];
        
        // Listen to mouse movement
        let mouseActive = false;
        window.addEventListener("mousemove", (e) => {
            mouseVortex.x = e.clientX;
            mouseVortex.y = e.clientY;
            mouseActive = true;
        });
        
        window.addEventListener("mouseleave", () => {
            mouseActive = false;
            mouseVortex.x = -1000;
            mouseVortex.y = -1000;
        });

        // Handle resize dynamically
        window.addEventListener("resize", () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            vortexes[0].x = width * 0.25;
            vortexes[0].y = height * 0.35;
            vortexes[1].x = width * 0.75;
            vortexes[1].y = height * 0.65;
        });

        // Initialize particles
        for (let i = 0; i < particleCount; i++) {
            particles.push(createParticle(true));
        }

        function createParticle(randomStart = false) {
            const speed = Math.random() * 1.5 + 0.6;
            const isOrange = Math.random() > 0.4;
            const baseColor = isOrange ? "rgba(232, 119, 34, " : "rgba(242, 242, 242, ";
            const baseOpacity = isOrange ? (Math.random() * 0.35 + 0.2) : (Math.random() * 0.2 + 0.15);
            return {
                x: randomStart ? Math.random() * width : -10,
                y: Math.random() * height,
                vx: speed * 1.2,
                vy: (Math.random() - 0.5) * 0.3,
                speed: speed,
                size: Math.random() * 1.8 + 0.6,
                baseColor: baseColor,
                baseOpacity: baseOpacity,
                history: []
            };
        }

        // Main Animation Frame
        function animate() {
            requestAnimationFrame(animate);

            // Clear canvas completely to keep background clean and avoid orange haze buildup
            const theme = document.documentElement.getAttribute("data-theme") || "dark";
            const bgClearColor = theme === "dark" ? "#070401" : "#F2F2F2";
            
            ctx.fillStyle = bgClearColor;
            ctx.fillRect(0, 0, width, height);

            // Update and draw particles
            particles.forEach((p, index) => {
                // Add current position to history before updating
                p.history.push({ x: p.x, y: p.y });
                if (p.history.length > historyLimit) {
                    p.history.shift();
                }

                // Apply wind flow
                p.vx += (p.speed * 0.02);
                p.vy += Math.sin(p.x * 0.004) * 0.01;

                // Apply vortex forces
                vortexes.forEach(v => {
                    const dx = v.x - p.x;
                    const dy = v.y - p.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    
                    if (dist < v.radius) {
                        const forceFactor = (1 - dist / v.radius);
                        const attractForce = forceFactor * v.attraction;
                        const rotateForce = forceFactor * v.rotation;
                        
                        const ax = (dx / dist) * attractForce;
                        const ay = (dy / dist) * attractForce;
                        
                        const rx = -(dy / dist) * rotateForce;
                        const ry = (dx / dist) * rotateForce;
                        
                        p.vx += ax + rx;
                        p.vy += ay + ry;
                    }
                });

                // Speed limit enforcement
                const currentSpeed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
                if (currentSpeed > maxSpeed) {
                    p.vx = (p.vx / currentSpeed) * maxSpeed;
                    p.vy = (p.vy / currentSpeed) * maxSpeed;
                }

                // Update position
                p.x += p.vx;
                p.y += p.vy;

                // Draw vector streak trails with progressive quadratic fading in opacity and size
                if (p.history.length > 1) {
                    for (let step = 1; step < p.history.length; step++) {
                        const pt1 = p.history[step - 1];
                        const pt2 = p.history[step];
                        
                        // Scale ratio from 0 (oldest) to 1 (newest)
                        const ratio = step / p.history.length;
                        
                        // Use quadratic curve for soft fade to 0 opacity
                        const opacity = p.baseOpacity * Math.pow(ratio, 2);
                        const size = p.size * (0.2 + 0.8 * ratio);
                        
                        ctx.beginPath();
                        ctx.moveTo(pt1.x, pt1.y);
                        ctx.lineTo(pt2.x, pt2.y);
                        ctx.strokeStyle = p.baseColor + opacity + ")";
                        ctx.lineWidth = size;
                        ctx.lineCap = "round";
                        ctx.stroke();
                    }
                }

                // Recycle offscreen wind streaks
                if (p.x > width + 20 || p.y < -20 || p.y > height + 20) {
                    particles[index] = createParticle(false);
                }
            });
        }

        animate();
    }
});
