// Dashboard JavaScript Module

class Dashboard {
    constructor() {
        this.currentSection = 'devotionals';
        this.init();
    }

    init() {
        this.initializeElements();
        this.attachEventListeners();
        this.loadUserData();
        this.initializeDevotionalForm();
    }

    initializeElements() {
        this.hamburgerBtn = document.getElementById('menu-toggle');
        this.sidebar = document.getElementById('sidebar');
        this.overlay = document.getElementById('sidebar-overlay');
        this.closeSidebarBtn = document.getElementById('close-sidebar');
        this.menuItems = document.querySelectorAll('.menu-item[data-section]');
        this.contentSections = document.querySelectorAll('.content-section');
    }

    attachEventListeners() {
        // Hamburger menu toggle
        this.hamburgerBtn.addEventListener('click', () => this.toggleSidebar());
        this.closeSidebarBtn.addEventListener('click', () => this.closeSidebar());
        this.overlay.addEventListener('click', () => this.closeSidebar());

        // Menu navigation
        this.menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                this.navigateToSection(section);
            });
        });

        // Escape key to close sidebar
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.sidebar.classList.contains('open')) {
                this.closeSidebar();
            }
        });
    }

    toggleSidebar() {
        this.sidebar.classList.toggle('open');
        this.overlay.classList.toggle('active');
        this.hamburgerBtn.classList.toggle('active');
    }

    closeSidebar() {
        this.sidebar.classList.remove('open');
        this.overlay.classList.remove('active');
        this.hamburgerBtn.classList.remove('active');
    }

    navigateToSection(section) {
        // Update active menu item
        this.menuItems.forEach(item => item.classList.remove('active'));
        document.querySelector(`[data-section="${section}"]`).classList.add('active');

        // Show/hide content sections
        this.contentSections.forEach(content => content.classList.remove('active'));
        document.getElementById(`${section}-section`).classList.add('active');

        this.currentSection = section;
        this.closeSidebar();

        // Load section-specific data
        this.loadSectionData(section);
    }

    loadSectionData(section) {
        switch (section) {
            case 'profile':
                this.loadProfileData();
                break;
            case 'subscriptions':
                this.loadSubscriptionData();
                break;
            case 'settings':
                this.loadSettingsData();
                break;
        }
    }

    async loadUserData() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) return;

            const response = await fetch('/api/user/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const userData = await response.json();
                this.updateProfileDisplay(userData);
            }
        } catch (error) {
            console.error('Erro ao carregar dados do usuário:', error);
        }
    }

    updateProfileDisplay(userData) {
        const nameElement = document.getElementById('user-name');
        const emailElement = document.getElementById('user-email');
        
        if (nameElement) nameElement.textContent = userData.name || 'Usuário';
        if (emailElement) emailElement.textContent = userData.email || '';
    }

    loadProfileData() {
        // Carregar estatísticas do perfil
        this.loadProfileStats();
    }

    async loadProfileStats() {
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/user/stats', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const stats = await response.json();
                document.getElementById('devotionals-count').textContent = stats.devotionalsCount || 0;
                document.getElementById('streak-count').textContent = stats.streakCount || 0;
            }
        } catch (error) {
            console.error('Erro ao carregar estatísticas:', error);
        }
    }

    loadSubscriptionData() {
        // Implementar carregamento de dados de assinatura
        console.log('Carregando dados de assinatura...');
    }

    loadSettingsData() {
        // Carregar configurações do usuário
        this.loadUserSettings();
    }

    async loadUserSettings() {
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/user/settings', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const settings = await response.json();
                document.getElementById('email-notifications').checked = settings.emailNotifications || false;
                document.getElementById('save-history').checked = settings.saveHistory !== false;
            }
        } catch (error) {
            console.error('Erro ao carregar configurações:', error);
        }
    }

    // Devotional Form Logic (moved from index.html)
    initializeDevotionalForm() {
        const form = document.getElementById('feeling-form');
        const generateBtn = document.getElementById('generate-btn');
        const sentimentoInput = document.getElementById('sentimento');
        const emojiOptions = document.querySelectorAll('.emoji-option');
        const backButton = document.getElementById('back-button');

        // Emoji selection
        emojiOptions.forEach(emoji => {
            emoji.addEventListener('click', function() {
                emojiOptions.forEach(e => e.classList.remove('selected'));
                this.classList.add('selected');
                
                const feeling = this.dataset.feeling;
                const currentText = sentimentoInput.value;
                const feelingText = this.textContent + ' ' + feeling;
                
                if (!currentText.includes(feelingText)) {
                    sentimentoInput.value = feelingText + ' - ' + currentText;
                }
                
                sentimentoInput.focus();
            });
        });

        // Form submission
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.generateDevotional();
            });
        }

        // Back button
        if (backButton) {
            backButton.addEventListener('click', () => {
                document.getElementById('devotional-result').style.display = 'none';
                document.getElementById('feeling-form-section').style.display = 'block';
            });
        }

        // Action buttons
        this.initializeActionButtons();
    }

    async generateDevotional() {
        const sentimentoInput = document.getElementById('sentimento');
        const generateBtn = document.getElementById('generate-btn');
        const btnText = generateBtn.querySelector('.btn-text');
        const loading = generateBtn.querySelector('.loading');

        if (!sentimentoInput.value.trim()) {
            alert('Por favor, compartilhe seus sentimentos.');
            return;
        }

        // Show loading state
        btnText.style.display = 'none';
        loading.style.display = 'inline-block';
        generateBtn.disabled = true;

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/generate_devotional', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    sentimento: sentimentoInput.value
                })
            });

            if (!response.ok) {
                throw new Error('Erro na resposta do servidor');
            }

            const data = await response.json();
            this.displayDevotional(data);

        } catch (error) {
            console.error('Erro:', error);
            alert('Erro ao gerar devocional. Tente novamente.');
        } finally {
            // Reset button state
            btnText.style.display = 'inline-block';
            loading.style.display = 'none';
            generateBtn.disabled = false;
        }
    }

    displayDevotional(data) {
        // Update devotional content
        document.getElementById('devotional-greeting').innerHTML = data.greeting || '';
        document.getElementById('devotional-verse-text').innerHTML = data.verse_text || '';
        document.getElementById('devotional-verse-reference').innerHTML = data.verse_reference || '';
        document.getElementById('devotional-content').innerHTML = data.content || '';
        
        // Set current date
        const now = new Date();
        document.querySelector('.devotional-date').textContent = 
            now.toLocaleDateString('pt-BR', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });

        // Show devotional result
        document.getElementById('feeling-form-section').style.display = 'none';
        document.getElementById('devotional-result').style.display = 'block';

        // Reset save button
        const saveBtn = document.getElementById('save-btn');
        saveBtn.textContent = '💾 Salvar';
        saveBtn.disabled = false;
    }

    initializeActionButtons() {
        // Share functionality
        const shareBtn = document.getElementById('share-btn');
        if (shareBtn) {
            shareBtn.addEventListener('click', () => this.shareDevotional());
        }

        // Save functionality
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveDevotional());
        }
    }

    shareDevotional() {
        const devotionalText = document.getElementById('devotional-content').textContent;
        const verseText = document.getElementById('devotional-verse-text').textContent;
        const verseRef = document.getElementById('devotional-verse-reference').textContent;
        
        const shareText = `${devotionalText}\n\n"${verseText}" - ${verseRef}\n\nGerado em: Devocionais Personalizados`;
        
        if (navigator.share) {
            navigator.share({
                title: 'Meu Devocional Personalizado',
                text: shareText
            });
        } else {
            navigator.clipboard.writeText(shareText).then(() => {
                alert('Devocional copiado para a área de transferência!');
            });
        }
    }

    async saveDevotional() {
        const sentimentoInput = document.getElementById('sentimento');
        const saveBtn = document.getElementById('save-btn');

        const devotionalData = {
            sentimento: sentimentoInput.value,
            greeting: document.getElementById('devotional-greeting').textContent,
            verse: {
                text: document.getElementById('devotional-verse-text').textContent,
                reference: document.getElementById('devotional-verse-reference').textContent
            },
            content: document.getElementById('devotional-content').textContent,
            date: new Date().toISOString()
        };

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/devotional/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(devotionalData)
            });

            if (response.ok) {
                saveBtn.innerHTML = '<span class="btn-icon">✅</span><span>Salvo</span>';
                saveBtn.disabled = true;
            } else {
                throw new Error('Erro ao salvar');
            }
        } catch (error) {
            console.error('Erro ao salvar:', error);
            alert('Erro ao salvar o devocional. Tente novamente.');
        }
    }
}

// Logout function
window.logout = function() {
    localStorage.removeItem('auth_token');
    window.location.href = '/';
};

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
    
    // Initialize MDC components if available
    if (typeof mdc !== 'undefined') {
        document.querySelectorAll('.mdc-text-field').forEach(el => {
            mdc.textField.MDCTextField.attachTo(el);
        });
    }
});
