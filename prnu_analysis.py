import numpy as np
from PIL import Image
import cv2
import io
import base64 

# الاستيراد الضروري لـ Wiener filter
try:
    from skimage.restoration import wiener 
except ImportError:
    pass 


def extract_noise_pattern(image_stream):
    """
    محاكاة استخلاص نمط الضوضاء (Noise Pattern) من الصورة (PRNU Approximation).
    """
    
    prnu_base64_image = None
    prnu_trust_score = 0.0
    # رسالة افتراضية في حالة عدم توفر المكتبة
    prnu_verdict = f"❌ خطأ: فشل استخلاص PRNU (قد تكون مكتبة scikit-image مفقودة)." 

    # 1. التحقق من توفر Wiener Filter
    try:
        wiener_func = wiener
    except NameError:
        image_stream.seek(0)
        return prnu_verdict, prnu_trust_score, prnu_base64_image

    try:
        # **خطوة حاسمة:** إعادة تعيين مؤشر الدفق إلى البداية.
        image_stream.seek(0) 
        
        # قراءة الصورة وتحويلها للرمادي للتبسيط
        img = Image.open(image_stream).convert('L') 
        
        # تحجيم الصورة لتسريع عملية Wiener Filter
        if img.width > 500 or img.height > 500:
            img = img.resize((500, 500), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
            
        img_np = np.array(img, dtype=np.float32)
        
        # 2. تطبيق مرشح Wiener لحساب الضوضاء المقدرة
        denoised_img = wiener(img_np, (5, 5), balance=0.01) 
        
        # حساب الضوضاء المقدرة
        noise_pattern = img_np - denoised_img
        
        # 3. حساب درجة الثقة (التحقق من التباين)
        noise_variance = np.var(noise_pattern)

        # القيم المرجعية (مُحاكاة):
        LOW_VAR_THRESHOLD = 30.0  
        HIGH_VAR_THRESHOLD = 150.0 
        
        prnu_trust_score = 0.0 

        if noise_variance < LOW_VAR_THRESHOLD:
            prnu_trust_score = 10.0 + 30.0 * (noise_variance / LOW_VAR_THRESHOLD)
            prnu_verdict = f"⚠️ تباين ضوضاء منخفض جداً ({noise_variance:.2f}). يشير إلى فلترة قوية/توليد آلي."
        elif noise_variance > HIGH_VAR_THRESHOLD:
            prnu_trust_score = 85.0
            prnu_verdict = f"✅ تباين ضوضاء طبيعي مرتفع ({noise_variance:.2f})."
        else:
            range_var = HIGH_VAR_THRESHOLD - LOW_VAR_THRESHOLD
            range_score = 85.0 - 40.0
            prnu_trust_score = 40.0 + range_score * ((noise_variance - LOW_VAR_THRESHOLD) / range_var)
            prnu_verdict = f"✅ تباين ضوضاء طبيعي ({noise_variance:.2f})."


        # 4. توليد صورة الضوضاء Base64
        noise_img_scaled = ((noise_pattern - noise_pattern.min()) / (noise_pattern.max() - noise_pattern.min())) * 255
        noise_img_scaled = noise_img_scaled.astype(np.uint8)
        
        prnu_img = Image.fromarray(noise_img_scaled, mode='L')
        buffer = io.BytesIO()
        prnu_img.save(buffer, format="PNG")
        prnu_base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # 5. إرجاع النتائج
        return prnu_verdict, float(prnu_trust_score), prnu_base64_image
        
    except Exception as e:
        prnu_verdict = f"❌ خطأ حرج في تحليل PRNU: {str(e)}"
        return prnu_verdict, 0.0, prnu_base64_image