document.addEventListener('DOMContentLoaded', () => {
    // =========================================================
    // 1. منطق معالجة الفورم وإرسال الصورة
    // =========================================================
    const uploadForm = document.getElementById('upload-form');
    const imageInput = document.getElementById('image-upload');
    const analyzeButton = document.getElementById('analyze-btn');
    const spinner = document.getElementById('loading-spinner');
    const resultsSection = document.getElementById('analysis-results');
    const downloadReportBtn = document.getElementById('download-report-btn');
    const triesStatusDiv = document.getElementById('tries-status'); // <--- عنصر جديد لإظهار حالة المحاولات

    let lastAnalysisResults = {};

    if (!uploadForm || !spinner || !resultsSection || !triesStatusDiv) {
        console.error("Critical Error: One or more required HTML elements are missing.");
        return;
    }

    // ----------------------------------------------
    // 🌟 دالة تحديث حالة المحاولات (للمحاولة المجانية) 🌟
    // ----------------------------------------------
    function updateTriesStatus(triesLeft) {
        if (triesLeft > 0) {
            triesStatusDiv.textContent = `لديك ${triesLeft} محاولة مجانية متبقية.`;
            analyzeButton.disabled = false;
            analyzeButton.textContent = 'تحليل الصورة';
            analyzeButton.classList.remove('btn-disabled'); 
        } else {
            triesStatusDiv.textContent = 'انتهت محاولاتك المجانية. يرجى الاشتراك للمزيد.';
            analyzeButton.disabled = true;
            analyzeButton.textContent = 'الاشتراك مطلوب';
            analyzeButton.classList.add('btn-disabled'); 
        }
    }

    // **أهمية:** استدعاء API جديد لمعرفة عدد المحاولات المتبقية عند تحميل الصفحة
    async function checkInitialTries() {
        try {
            // يتصل بنقطة النهاية الجديدة في app_flask.py
            const response = await fetch('/api/check_tries');
            if (response.ok) {
                const data = await response.json();
                updateTriesStatus(data.tries_left);
            } else {
                // إذا فشل الاتصال الأولي (قد يكون الخادم غير متوفر)، افترض محاولة واحدة مبدئياً
                updateTriesStatus(1);
            }
        } catch (e) {
            console.error("Failed to check initial tries:", e);
            updateTriesStatus(1);
        }
    }

    // استدعاء الدالة عند تحميل الصفحة
    checkInitialTries(); 

    uploadForm.addEventListener('submit', async function(event) {
        event.preventDefault(); 

        const file = imageInput.files[0];

        if (!file) {
            alert("الرجاء اختيار صورة للتحليل أولاً.");
            return;
        }

        // 1. تفعيل حالة التحميل وإعادة تعيين العرض
        spinner.classList.remove('hidden');
        analyzeButton.disabled = true;
        analyzeButton.textContent = 'جاري التحليل...';
        
        // إعادة تعيين النتائج السابقة
        document.getElementById('final-verdict-msg').textContent = 'جاري التقييم...';
        document.getElementById('final-verdict-msg').className = 'score-indicator';
        
        // إعادة تعيين جميع بطاقات النتائج
        document.getElementById('ela-score-display').textContent = '--%';
        document.getElementById('prnu-score-display').textContent = '--%';
        document.getElementById('ai-score-display').textContent = '--%';
        
        // **تصحيح المعرّفات هنا:**
        document.getElementById('ela-image').src = ''; 
        document.getElementById('prnu-image').src = ''; 
        document.getElementById('gradcam-image').src = '';
        
        document.getElementById('ela-score-msg').textContent = '---';
        document.getElementById('prnu-analysis-msg').textContent = '---';
        document.getElementById('ai-analysis-result').textContent = '---';
        downloadReportBtn.classList.add('hidden');


        // 2. إرسال البيانات
        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            // التحقق من حالة الاستجابة قبل محاولة قراءة JSON
            if (!response.ok) {
                 // إذا كانت حالة الاستجابة ليست 200 OK، حاول قراءة رسالة الخطأ
                let error_text = `HTTP Error: ${response.status} ${response.statusText}`;
                
                try {
                    const error_data = await response.json();
                    if (error_data && error_data.error) {
                        error_text = error_data.error;
                    } 
                    
                    // 🌟 معالجة الخطأ 402 (انتهت المحاولات)
                    if (response.status === 402 && typeof error_data.tries_left !== 'undefined') {
                        updateTriesStatus(error_data.tries_left); // تحديث الواجهة إلى 0
                    } else if (response.status === 413) {
                         error_text = "حجم الملف كبير جداً. الحد الأقصى المسموح به هو 10 ميجابايت.";
                    }
                } catch (e) {
                    // فشل قراءة JSON (الخادم أرجع HTML أو نص عادي)
                    console.error("Failed to parse error JSON:", e);
                }
                
                // عرض رسالة الخطأ الواضحة في الواجهة
                document.getElementById('final-verdict-msg').textContent = 'فشل التحليل';
                document.getElementById('final-verdict-msg').classList.add('tainted');
                document.getElementById('ai-analysis-result').textContent = error_text;
                resultsSection.classList.remove('hidden');

            } else {
                // حالة النجاح (200 OK)
                const data = await response.json();
                lastAnalysisResults = data;
                displayResults(data);
                downloadReportBtn.classList.remove('hidden');
                
                // 🌟 تحديث حالة المحاولات بعد التحليل الناجح
                if (typeof data.tries_left !== 'undefined') {
                    updateTriesStatus(data.tries_left); 
                }
            }


        } catch (error) {
            // فشل في الاتصال بالشبكة (الخادم لا يعمل أو مشكلة CORS/DNS)
            alert(`فشل في الاتصال بالخادم: ${error.message}`);
            document.getElementById('final-verdict-msg').textContent = 'خطأ في الاتصال';
            document.getElementById('final-verdict-msg').classList.add('tainted');
            document.getElementById('ai-analysis-result').textContent = `فشل في الاتصال بالشبكة: ${error.message}. تأكد من أن خادم Python يعمل.`;
            resultsSection.classList.remove('hidden'); 
            
        } finally {
            // 3. تعطيل حالة التحميل وتحديث الزر (يتم استدعاء updateTriesStatus لاحقاً لإعادة التفعيل إذا كانت المحاولات متبقية)
            spinner.classList.add('hidden');
            analyzeButton.disabled = false;
            // يتم تعيين النص الصحيح للزر بواسطة updateTriesStatus
            if (analyzeButton.textContent === 'جاري التحليل...') {
                analyzeButton.textContent = 'تحليل صورة أخرى';
            }
        }
    });

    // =========================================================
    // 2. دالة عرض النتائج
    // =========================================================

    function displayResults(results) {
        // 1. عرض النتائج الرقمية
        document.getElementById('ela-score-display').textContent = `${results.ela_score.toFixed(1)}%`;
        document.getElementById('prnu-score-display').textContent = `${results.prnu_score.toFixed(1)}%`;
        document.getElementById('ai-score-display').textContent = `${results.ai_score_raw.toFixed(1)}%`;

        document.getElementById('ela-score-msg').textContent = results.ela_message;
        document.getElementById('prnu-analysis-msg').textContent = results.prnu_message;
        document.getElementById('ai-analysis-result').textContent = results.ai_message;

        // 2. عرض الصور (Base64) - تصحيح المعرّفات هنا
        document.getElementById('ela-image').src = `data:image/png;base64,${results.ela_base64_image}`;
        document.getElementById('prnu-image').src = `data:image/png;base64,${results.prnu_base64_image}`;
        
        if (results.gradcam_base64_image) {
            document.getElementById('gradcam-image').src = `data:image/png;base64,${results.gradcam_base64_image}`;
            document.getElementById('gradcam-message').textContent = 'خريطة Grad-CAM (مناطق تركيز AI)';
        } else {
            document.getElementById('gradcam-image').src = '';
            document.getElementById('gradcam-message').textContent = 'فشل توليد خريطة Grad-CAM التفسيرية.';
        }


        // 3. تحديد القرار النهائي
        const finalScore = results.final_combined_score;
        const verdictMsg = document.getElementById('final-verdict-msg');
        verdictMsg.textContent = `${finalScore.toFixed(1)}%`;
        verdictMsg.className = 'score-indicator'; 

        if (finalScore >= 80) {
            verdictMsg.classList.add('clean');
            document.getElementById('final-verdict-msg').textContent = 'أصيل/موثوق به';
        } else if (finalScore >= 50) {
            verdictMsg.classList.add('caution');
            document.getElementById('final-verdict-msg').textContent = 'محتمل التلاعب (حذر)';
        } else {
            verdictMsg.classList.add('tainted');
            document.getElementById('final-verdict-msg').textContent = 'مزور/تم التلاعب به';
        }
        
        // 4. عرض قسم النتائج
        resultsSection.classList.remove('hidden');
    }

    // =========================================================
    // 3. منطق توليد التقرير
    // =========================================================

    downloadReportBtn.addEventListener('click', async function() {
        if (Object.keys(lastAnalysisResults).length === 0) {
            alert('الرجاء إجراء تحليل أولاً قبل محاولة تحميل التقرير.');
            return;
        }

        downloadReportBtn.textContent = 'جاري توليد التقرير...';
        downloadReportBtn.disabled = true;

        try {
            const response = await fetch('/api/download_report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(lastAnalysisResults)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            let filename = 'Sedq_Analysis_Report.pdf';
            const contentDisposition = response.headers.get('Content-Disposition');
            if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
                filename = contentDisposition.split('filename=')[1].trim().replace(/['"]/g, '');
            }
            a.download = filename;
            
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            
            alert('تم تحميل التقرير بنجاح!');

        } catch (e) {
            console.error('Download error:', e);
            alert(`فشل في تحميل تقرير PDF: ${e.message}`);
        } finally {
            downloadReportBtn.textContent = 'تحميل تقرير PDF مفصل';
            downloadReportBtn.disabled = false;
        }
    });


    // =========================================================
    // 4. رسومات الخلفية المتحركة (Canvas) 
    // =========================================================
    const canvas = document.getElementById('bg-canvas');
    
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let circles = [];
        
        const style = getComputedStyle(document.body);
        const bgColor = style.getPropertyValue('--color-background').trim();
        const match = bgColor.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
        const bgColorR = match ? parseInt(match[1], 16) : 56;
        const bgColorG = match ? parseInt(match[2], 16) : 98;
        const bgColorB = match ? parseInt(match[3], 16) : 99;


        const numCircles = 6;       
        const maxRadius = 150;      
        const minRadius = 80;       
        const maxSpeed = 0.2;       
        const minSpeed = 0.05;      
        
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            init(); 
        });
        
        class Circle {
            constructor() {
                this.radius = Math.random() * (maxRadius - minRadius) + minRadius;
                this.x = Math.random() * (canvas.width - this.radius * 2) + this.radius;
                this.y = Math.random() * (canvas.height - this.radius * 2) + this.radius;
                
                this.dx = (Math.random() - 0.5) * (maxSpeed - minSpeed) + minSpeed;
                this.dy = (Math.random() - 0.5) * (maxSpeed - minSpeed) + minSpeed;
                
                const primaryColor = style.getPropertyValue('--color-primary').trim();
                this.color = primaryColor || '#DDC5A8'; 
                this.alpha = Math.random() * (0.15 - 0.05) + 0.05; 
            }

            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2, false);
                const hex = this.color.slice(1);
                const r = parseInt(hex.substring(0, 2), 16);
                const g = parseInt(hex.substring(2, 4), 16);
                const b = parseInt(hex.substring(4, 6), 16);
                
                ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${this.alpha})`;
                ctx.fill();
            }

            update() {
                if (this.x + this.radius > canvas.width || this.x - this.radius < 0) {
                    this.dx = -this.dx;
                }
                if (this.y + this.radius > canvas.height || this.y - this.radius < 0) {
                    this.dy = -this.dy;
                }

                this.x += this.dx;
                this.y += this.dy;

                this.draw();
            }
        }

        function init() {
            circles = [];
            for (let i = 0; i < numCircles; i++) {
                circles.push(new Circle());
            }
        }

        function animate() {
            requestAnimationFrame(animate);
            
            ctx.fillStyle = `rgba(${bgColorR}, ${bgColorG}, ${bgColorB}, 0.1)`; 
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            for (let i = 0; i < circles.length; i++) {
                circles[i].update();
            }
        }

        init();
        animate();
    }
    
    // =========================================================
    // 5. منطق تحميل ملفات HTML أخرى (مثل payment.html)
    // =========================================================
    const paymentForm = document.getElementById('payment-form');
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const selectedPlan = document.getElementById('plan_select').value;
            if (!selectedPlan) {
                alert('الرجاء اختيار باقة الدفع أولاً.');
                return;
            }
            alert(`تمت محاكاة اشتراكك بنجاح في خطة ${selectedPlan}!\nسيتم تفعيل الميزات الاحترافية.`);
        });
    }
    

});