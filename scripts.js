document.addEventListener('DOMContentLoaded', () => {
    // =========================================================
    // 1. المتغيرات الرئيسية وعناصر الـ HTML
 // =========================================================
// 7. منطق محاكاة تكامل أبشر الأمني (الذي يرسل لـ API صدق)
// =========================================================

const abshrForm = document.getElementById('abshr-upload-form');
const abshrResultsSection = document.getElementById('abshr-results');
const abshrSpinner = document.getElementById('loading-spinner');
const finalVerdictMsg = document.getElementById('final-verdict-message');
const confidenceScoreDisplay = document.getElementById('confidence-score');
const statusMsg = document.getElementById('status-message');
const verdictContainer = document.getElementById('verdict-container');
const downloadReportBtn = document.getElementById('download-report-btn');
const fileReportBtn = document.getElementById('file-report-btn');


function updateAbshrResults(data) {
    abshrResultsSection.classList.remove('hidden');

    const score = data.confidence_score;
    const verdict = data.abshr_verdict;
    const reportUrl = data.report_url; // '/api/report'

    confidenceScoreDisplay.textContent = `${score.toFixed(2)}%`;
    statusMsg.textContent = '✅ اكتمل التحليل الأمني بنجاح.';

    // إزالة جميع فئات القرار أولاً
    verdictContainer.classList.remove('verdict-clean', 'verdict-caution', 'verdict-tainted');
    
    // 1. تحديد القرار الأمني
    if (verdict === 'CLEAN') {
        finalVerdictMsg.textContent = '✅ أصالة مُؤكَّدة: الوثيقة نظيفة وموثوقة.';
        verdictContainer.classList.add('verdict-clean');
        downloadReportBtn.classList.remove('hidden');
        fileReportBtn.classList.add('hidden'); // إخفاء زر البلاغ
    } else if (verdict === 'CAUTION') {
        finalVerdictMsg.textContent = '⚠️ تنبيه: احتمالية تلاعب، يرجى مراجعة التقرير.';
        verdictContainer.classList.add('verdict-caution');
        downloadReportBtn.classList.remove('hidden');
        fileReportBtn.classList.remove('hidden'); // إظهار زر البلاغ
    } else { // FORGED
        finalVerdictMsg.textContent = '❌ تزوير مُؤكَّد: تم الكشف عن تلاعب كبير بالوثيقة.';
        verdictContainer.classList.add('verdict-tainted');
        downloadReportBtn.classList.remove('hidden');
        fileReportBtn.classList.remove('hidden'); // إظهار زر البلاغ
    }

    // 2. ربط زر التقرير بـ URL الذي يعيده الخادم
    downloadReportBtn.onclick = () => {
        window.open(reportUrl, '_blank');
    };
    
    // 3. محاكاة البلاغ الأمني 
    fileReportBtn.onclick = () => {
        alert('✅ تم تسجيل بلاغ أمني بالوثيقة، سيتم تحويلك لجهة الاختصاص لمتابعة الإجراء.');
    };
}


if (abshrForm && abshrSpinner) {
    abshrForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // إخفاء النتائج القديمة وإظهار شريط التحميل
        abshrResultsSection.classList.add('hidden');
        abshrSpinner.classList.remove('hidden');
        statusMsg.textContent = 'جاري إرسال الملف وبدء التحليل الأمني...';
        
        const formData = new FormData(abshrForm);
        const imageFile = document.getElementById('image-upload').files[0];

        if (!imageFile) {
             statusMsg.textContent = '❌ الرجاء اختيار صورة أولاً.';
             abshrSpinner.classList.add('hidden');
             return;
        }

        try {
            // الاستدعاء لـ API صدق
            const response = await fetch('/api/abshr/security-forensics', {
                method: 'POST',
                body: formData
            });

            abshrSpinner.classList.add('hidden');

            const data = await response.json();

            if (data.status === 'success') {
                // استخدام البيانات لتحديث الواجهة بالختم والقرار.
                updateAbshrResults(data); 
            } else {
                // التعامل مع الأخطاء
                statusMsg.textContent = `❌ فشل التحليل: ${data.message || 'حدث خطأ غير معروف'}`;
            }

        } catch (error) {
            abshrSpinner.classList.add('hidden');
            console.error('Fetch Error:', error);
            statusMsg.textContent = `❌ خطأ في الاتصال بالخادم: ${error.message}`;
        }
    });
} let lastAnalysisResults = {};

    if (!uploadForm || !spinner || !resultsSection || !triesStatusDiv) {
        console.error("Critical Error: One or more required HTML elements are missing.");
        return;
    }

    // ----------------------------------------------
    // 🌟 دالة تحديث حالة المحاولات (للمحاولة المجانية والاشتراك) 🌟
    // ----------------------------------------------
    function updateTriesStatus(triesLeft) {
        // حالة المشترك (الخادم يرجع -1)
        if (triesLeft === -1) {
            triesStatusDiv.textContent = 'اشتراك فعال: تحليل غير محدود.';
            analyzeButton.disabled = false;
            analyzeButton.textContent = 'تحليل صورة أخرى';
            analyzeButton.classList.remove('btn-disabled');
        } else if (triesLeft > 0) {
            // حالة المحاولات المتبقية
            triesStatusDiv.textContent = `لديك ${triesLeft} محاولة مجانية متبقية.`;
            analyzeButton.disabled = false;
            analyzeButton.textContent = 'تحليل الصورة';
            analyzeButton.classList.remove('btn-disabled');
        } else {
            // حالة انتهاء المحاولات (triesLeft <= 0)
            triesStatusDiv.textContent = 'انتهت محاولاتك المجانية. يرجى الاشتراك للمزيد.';
            analyzeButton.disabled = true;
            analyzeButton.textContent = 'الاشتراك مطلوب';
            analyzeButton.classList.add('btn-disabled');
        }
    }

    // **تم حذف دالة checkInitialTries() واستدعائها.**
    // **بدلاً من ذلك، نفترض وجود محاولة واحدة مبدئياً، وسيتم تحديثها تلقائياً بعد أول تحليل ناجح.**
    updateTriesStatus(1);


    // =========================================================
    // 2. دالة معالجة إرسال الصورة
    // =========================================================

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
        
        document.getElementById('ela-score-display').textContent = '--%';
        document.getElementById('prnu-score-display').textContent = '--%';
        document.getElementById('ai-score-display').textContent = '--%';
        
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
            // الطلب الصحيح (POST)
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                // حالة الفشل (402, 413, 500)
                let error_text = `HTTP Error: ${response.status} ${response.statusText}`;
                let error_data = {};
                
                try {
                    error_data = await response.json();
                    if (error_data && error_data.error) {
                        error_text = error_data.error;
                    } 
                    
                    // تحديث حالة المحاولات عند خطأ 402 (انتهت المحاولات)
                    if (response.status === 402 && typeof error_data.tries_left !== 'undefined') {
                        updateTriesStatus(error_data.tries_left); 
                    } else if (response.status === 413) {
                         error_text = "حجم الملف كبير جداً. الحد الأقصى المسموح به هو 10 ميجابايت.";
                    }
                } catch (e) {
                    console.error("Failed to parse error JSON:", e);
                }
                
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
            // فشل في الاتصال بالشبكة
            alert(`فشل في الاتصال بالخادم: ${error.message}. تأكد من أن خادم Python يعمل.`);
            document.getElementById('final-verdict-msg').textContent = 'خطأ في الاتصال';
            document.getElementById('final-verdict-msg').classList.add('tainted');
            document.getElementById('ai-analysis-result').textContent = `فشل في الاتصال بالشبكة: ${error.message}.`;
            resultsSection.classList.remove('hidden'); 
            
        } finally {
            spinner.classList.add('hidden');
            // يتم تعيين حالة الزر الصحيحة بواسطة updateTriesStatus
            if (analyzeButton.textContent === 'جاري التحليل...') {
                analyzeButton.textContent = 'تحليل صورة أخرى';
                analyzeButton.disabled = false; // إذا لم يقم updateTriesStatus بتعطيله
            }
        }
    });

    // =========================================================
    // 3. دالة عرض النتائج
    // =========================================================

    function displayResults(results) {
        document.getElementById('ela-score-display').textContent = `${results.ela_score.toFixed(1)}%`;
        document.getElementById('prnu-score-display').textContent = `${results.prnu_score.toFixed(1)}%`;
        document.getElementById('ai-score-display').textContent = `${results.ai_score_raw.toFixed(1)}%`;

        document.getElementById('ela-score-msg').textContent = results.ela_message;
        document.getElementById('prnu-analysis-msg').textContent = results.prnu_message;
        document.getElementById('ai-analysis-result').textContent = results.ai_message;

        document.getElementById('ela-image').src = `data:image/png;base64,${results.ela_base64_image}`;
        document.getElementById('prnu-image').src = `data:image/png;base64,${results.prnu_base64_image}`;
        
        const gradcamMsg = document.getElementById('gradcam-message');
        if (results.gradcam_base64_image) {
            document.getElementById('gradcam-image').src = `data:image/png;base64,${results.gradcam_base64_image}`;
            gradcamMsg.textContent = 'خريطة Grad-CAM (مناطق تركيز AI)';
        } else {
            document.getElementById('gradcam-image').src = '';
            gradcamMsg.textContent = 'فشل توليد خريطة Grad-CAM التفسيرية.';
        }


        // 3. تحديد القرار النهائي
        const finalScore = results.final_combined_score;
        const verdictMsg = document.getElementById('final-verdict-msg');
        verdictMsg.textContent = `${finalScore.toFixed(1)}%`;
        verdictMsg.className = 'score-indicator'; 

        if (finalScore >= 80) {
            verdictMsg.classList.add('clean');
            verdictMsg.textContent = 'أصيل/موثوق به';
        } else if (finalScore >= 50) {
            verdictMsg.classList.add('caution');
            verdictMsg.textContent = 'محتمل التلاعب (حذر)';
        } else {
            verdictMsg.classList.add('tainted');
            verdictMsg.textContent = 'مزور/تم التلاعب به';
        }
        
        resultsSection.classList.remove('hidden');
    }

    // =========================================================
    // 4. منطق توليد التقرير
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
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }

            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            let filename = `Sedq_Analysis_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
            const contentDisposition = response.headers.get('Content-Disposition');
            if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
                filename = contentDisposition.split('filename=')[1].trim().replace(/['"]/g, '');
            }
            a.download = filename;
            
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            
            // alert('تم تحميل التقرير بنجاح!'); // إلغاء التنبيه لتجنب إيقاف سير العمل

        } catch (e) {
            console.error('Download error:', e);
            alert(`فشل في تحميل تقرير PDF: ${e.message}`);
        } finally {
            downloadReportBtn.textContent = 'تحميل تقرير PDF مفصل';
            downloadReportBtn.disabled = false;
        }
    });


    // =========================================================
    // 5. رسومات الخلفية المتحركة (Canvas) 
    // =========================================================
    const canvas = document.getElementById('bg-canvas');
    
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let circles = [];
        
        const style = getComputedStyle(document.body);
        
        // استخراج ألوان الخلفية من CSS
        const bgColorHex = style.getPropertyValue('--color-background').trim();
        const hexToRgb = (hex) => {
            const match = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
            return match ? [parseInt(match[1], 16), parseInt(match[2], 16), parseInt(match[3], 16)] : [56, 98, 99]; // Default
        };
        const [bgColorR, bgColorG, bgColorB] = hexToRgb(bgColorHex);


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
    // 6. منطق الدفع (محاكاة)
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
            // ⚠️ في التطبيق الحقيقي، هذا هو المكان الذي يتم فيه الاتصال بـ /api/create-checkout-session
            alert(`تمت محاكاة اشتراكك بنجاح في خطة ${selectedPlan}!\nسيتم تفعيل الميزات الاحترافية.`);
        });
    }
    

});
// في ملف scripts.js، أضف هذا المنطق في مكان مناسب (مثلاً في نهاية الملف):

// =========================================================
// 7. منطق محاكاة تكامل أبشر الأمني
// =========================================================

const abshrForm = document.getElementById('abshr-upload-form');
const abshrResults = document.getElementById('abshr-results');
const abshrSpinner = document.getElementById('loading-spinner');

if (abshrForm) {
    abshrForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        abshrResults.classList.add('hidden');
        abshrSpinner.classList.remove('hidden');
        document.getElementById('abshr-status-msg').textContent = 'جاري إرسال الطلب لـ صِدق...';
        
        const formData = new FormData(abshrForm);

        try {
            const response = await fetch('/api/abshr/security-forensics', {
                method: 'POST',
                body: formData
            });

            abshrSpinner.classList.add('hidden');
            const data = await response.json();

            if (data.status === 'success') {
                updateAbshrResults(data);
            } else {
                // حالة خطأ من الـ API (مثل 400 أو 500)
                updateAbshrError(data.message_ar || 'فشل الاتصال بخدمة صدق');
            }

        } catch (error) {
            abshrSpinner.classList.add('hidden');
            updateAbshrError('فشل الاتصال بالخادم. تحقق من تشغيل محرك صِدق.');
            console.error('Fetch error:', error);
        }
    });
}

// ... داخل ملف scripts.js ...

function updateAbshrResults(data) {
    const resultsSection = document.getElementById('abshr-results');
    const verdictBox = document.getElementById('verdict-container'); // ⬅️ الاسم الجديد
    const finalVerdictMsg = document.getElementById('final-verdict-message');
    const confidenceScore = document.getElementById('confidence-score');
    const downloadReportBtn = document.getElementById('download-report-btn');
    const fileReportBtn = document.getElementById('file-report-btn');

    resultsSection.classList.remove('hidden');

    const score = data.confidence_score;
    const verdict = data.abshr_verdict;
    const reportUrl = data.report_url;

    confidenceScore.textContent = `${score.toFixed(2)}%`;

    // 1. تحديد القرار الأمني
    verdictBox.classList.remove('verdict-clean', 'verdict-caution', 'verdict-tainted');

    if (verdict === 'CLEAN') {
        finalVerdictMsg.textContent = '✅ أصالة مُؤكَّدة: الوثيقة نظيفة وموثوقة.';
        verdictBox.classList.add('verdict-clean');
        downloadReportBtn.classList.remove('hidden');
        fileReportBtn.classList.add('hidden'); // إخفاء زر البلاغ
    } else if (verdict === 'CAUTION') {
        finalVerdictMsg.textContent = '⚠️ تنبيه: احتمالية تلاعب، يجب التحقق يدوياً.';
        verdictBox.classList.add('verdict-caution');
        downloadReportBtn.classList.remove('hidden');
        fileReportBtn.classList.remove('hidden'); // إظهار زر البلاغ
    } else { // FORGED (أو أي شيء آخر)
        finalVerdictMsg.textContent = '❌ تزوير مُؤكَّد: تم الكشف عن تلاعب كبير بالوثيقة.';
        verdictBox.classList.add('verdict-tainted');
        downloadReportBtn.classList.remove('hidden');
        fileReportBtn.classList.remove('hidden'); // إظهار زر البلاغ
    }

    // 2. ربط زر التقرير بـ URL الذي يعيده صدق
    downloadReportBtn.onclick = () => {
        window.open(reportUrl, '_blank');
    };
    
    // 3. محاكاة البلاغ الأمني (لتكملة التدفق)
    fileReportBtn.onclick = () => {
        alert('✅ تم تسجيل بلاغ أمني بالوثيقة، سيتم تحويلك لجهة الاختصاص لمتابعة الإجراء.');
        // يمكن هنا إضافة منطق لتوجيه المستخدم إلى صفحة بلاغ في أبشر
    };
}
// ... باقي محتوى scripts.js ...
function updateAbshrError(message) {
    const statusMsg = document.getElementById('abshr-status-msg');
    const resultsSection = document.getElementById('abshr-results');
    
    statusMsg.textContent = `❌ ${message}`;
    resultsSection.classList.add('hidden');
}
