import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.optimizers import Adam 
import numpy as np
from PIL import Image, ImageChops # ImageChops ضرورية لـ ELA
import io
import cv2
import base64 
from tf_keras_vis.gradcam import Gradcam 
from tf_keras_vis.utils.model_modifiers import ReplaceToLinear 
from tf_keras_vis.utils import normalize 

# الاستيراد من ملف تحليل الضوضاء
try:
    from prnu_analysis import extract_noise_pattern
except ImportError:
    print("WARNING: فشل استيراد prnu_analysis. التحليل سيعتمد على AI و ELA فقط.")
    def extract_noise_pattern(image_stream):
        # محاكاة لـ PRNU في حالة الفشل
        return "❌ محاكاة: تحليل PRNU غير متوفر", 0.0, None

# حجم الصورة الذي يتطلبه النموذج 
IMG_SIZE = 128
MODEL_PATH = 'forensics_model.h5'

# =========================================================
# 1. تعريف النموذج وتحميله
# =========================================================

# (بناء النموذج كما هو في ملفك، مع التأكد من وجود forensics_model.h5)
def build_forensics_model():
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 3)),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(64, activation='relu'),
        Dense(1, activation='sigmoid') 
    ])
    return model

try:
    LOADED_MODEL = load_model(MODEL_PATH)
    # 🌟🌟🌟 الإصلاح 1: إضافة اسم الإخراج للنموذج المحمّل 🌟🌟🌟
    if not LOADED_MODEL.output_names:
        LOADED_MODEL.output_names = ['output_1']
        
    print(f"✅ نجاح: تم تحميل نموذج AI من {MODEL_PATH}")
except Exception as e:
# ... (بقية منطق التحميل يبقى كما هو) ...
    print(f"❌ فشل تحميل نموذج AI: {e}. سيتم إيقاف التحليل الذكي.")
    LOADED_MODEL = None


# =========================================================
# 2. دالة تحليل ELA (Error Level Analysis) - الآن كاملة
# =========================================================

def analyze_ela(image_stream, quality=95, scale_factor=15):
    """
    تحليل مستوى الخطأ (ELA) لتحديد المناطق التي تم تعديلها.
    تقوم بحفظ الصورة ثم إعادة فتحها بضغط 95% لمعرفة الفرق.
    """
    image_stream.seek(0)
    original_img = Image.open(image_stream).convert('RGB')
    
    # 1. إعادة حفظ الصورة بجودة أقل (95%)
    ela_buffer = io.BytesIO()
    original_img.save(ela_buffer, format='JPEG', quality=quality)
    ela_buffer.seek(0)
    compressed_img = Image.open(ela_buffer).convert('RGB')
    
    # 2. حساب الفرق (Error) بين الأصل والمضغوط
    diff = ImageChops.difference(original_img, compressed_img)
    
    # 3. تضخيم الإشارات لسهولة الرؤية (Scaling)
    # نستخدم عامل مقياس لتضخيم الفروقات اللونية
    diff_array = np.array(diff).astype(np.float32) * scale_factor
    diff_array = np.clip(diff_array, 0, 255).astype(np.uint8)
    ela_img = Image.fromarray(diff_array)

    # 4. حفظ صورة ELA المشفرة لغرض التقرير
    ela_img_buffer = io.BytesIO()
    ela_img.save(ela_img_buffer, format='PNG')
    ela_base64_image = base64.b64encode(ela_img_buffer.getvalue()).decode('utf-8')
    
    # 5. تحليل النتيجة (تبسيط: حساب متوسط الاختلاف)
    mean_error = np.mean(diff_array)
    
    # تحديد درجة ELA
    if mean_error < 5.0:
        ela_score = 90.0 # أصالة عالية
        ela_verdict = f"✅ تباين منخفض جداً في ELA ({mean_error:.2f})."
    elif mean_error < 15.0:
        ela_score = 75.0 # طبيعي
        ela_verdict = f"🟡 تباين طبيعي في ELA ({mean_error:.2f})."
    else:
        ela_score = 30.0 # تزوير
        ela_verdict = f"❌ تباين عالٍ في ELA ({mean_error:.2f}). يشير إلى مناطق معدلة."
        
    return ela_score, ela_verdict, ela_base64_image


# =========================================================
# 3. دالة التحليل الجنائي الشاملة
# =========================================================

def analyze_full_forensics(image_stream):
    
    # ----------------------------------------------------
    # أ. استخلاص بيانات EXIF الأساسية
    # ----------------------------------------------------
    image_stream.seek(0)
    img = Image.open(image_stream)
    metadata = {
        'make': img.getexif().get(271) if img.getexif() else 'غير متوفر',
        'model': img.getexif().get(272) if img.getexif() else 'غير متوفر',
        'datetime': img.getexif().get(36867) if img.getexif() else 'غير متوفر',
        'format': img.format,
        'size': f"{img.width}x{img.height}",
    }
    
    # ----------------------------------------------------
    # ب. تحليل PRNU
    # ----------------------------------------------------
    prnu_verdict, prnu_score, prnu_img_base64 = extract_noise_pattern(image_stream)
    
    # ----------------------------------------------------
    # ج. تحليل ELA
    # ----------------------------------------------------
    ela_score, ela_verdict, ela_img_base64 = analyze_ela(image_stream)
    
    # ----------------------------------------------------
    # د. تحليل الذكاء الاصطناعي (AI CNN)
    # ----------------------------------------------------
    ai_trust_score = 50.0 
    gradcam_img_base64 = None
    ai_verdict = "❌ فشل التحليل بواسطة الذكاء الاصطناعي (النموذج مفقود أو غير فعال)."

    if LOADED_MODEL:
        try:
            image_stream.seek(0)
            img_resized = Image.open(image_stream).convert('RGB').resize((IMG_SIZE, IMG_SIZE))
            img_array = np.array(img_resized) / 255.0
            
            # التنبؤ
            prediction = LOADED_MODEL.predict(np.expand_dims(img_array, axis=0))
            ai_trust_score = (1.0 - prediction[0][0]) * 100.0 # الثقة في الأصالة

            if ai_trust_score > 70:
                ai_verdict = f"✅ تحليل AI: ثقة عالية في الأصالة ({ai_trust_score:.2f}%)"
            elif ai_trust_score > 40:
                ai_verdict = f"🟡 تحليل AI: نتيجة مشتبه بها. ({ai_trust_score:.2f}%)"
            else:
                ai_verdict = f"❌ تحليل AI: كشف تلاعب أو توليد آلي. ({ai_trust_score:.2f}%)"
            
            # ----------------------------------------------------
            # هـ. منطق توليد Grad-CAM (للتفسير)
            # ----------------------------------------------------
            # يجب تعريف دالة الهدف هنا، ولغرض التدريب نستخدم النتيجة مباشرة
            def loss(output):
                return (output[0][0])
                
            gradcam = Gradcam(LOADED_MODEL, model_modifier=ReplaceToLinear(), clone=True)
            cam = gradcam(loss, img_array[np.newaxis, ...], penultimate_layer=-1)
            heatmap = np.uint8(cam[0] * 255)
            
            # حفظ صورة Grad-CAM
            gradcam_img = Image.fromarray(heatmap, 'L').convert('RGB')
            gradcam_img_buffer = io.BytesIO()
            gradcam_img.save(gradcam_img_buffer, format='PNG')
            gradcam_img_base64 = base64.b64encode(gradcam_img_buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"Critical error in AI analysis/GradCAM: {e}")

        
    # ----------------------------------------------------
    # و. دمج النتائج وتقرير النتيجة النهائية
    # ----------------------------------------------------
    
    final_score_unclamped = (0.4 * ai_trust_score) + (0.3 * prnu_score) + (0.3 * ela_score)
    final_score = np.clip(final_score_unclamped, 0.0, 100.0) 

    # بناء رسالة القرار الأمني (الختم)
    if final_score < 40:
        abshr_verdict = "FORGED"
    elif final_score < 75:
        abshr_verdict = "CAUTION"
    else:
        abshr_verdict = "CLEAN"
        
    
    # ----------------------------------------------------
    # ز. تجميع كل البيانات في قاموس واحد
    # ----------------------------------------------------
    
    analysis_results = {
        'final_score': final_score,
        'abshr_verdict': abshr_verdict,
        'metadata': metadata,
        
        'ai_score': ai_trust_score,
        'ai_verdict': ai_verdict,
        'gradcam_img_base64': gradcam_img_base64,
        
        'prnu_score': prnu_score,
        'prnu_verdict': prnu_verdict,
        'prnu_img_base64': prnu_img_base64,
        
        'ela_score': ela_score,
        'ela_verdict': ela_verdict,
        'ela_img_base64': ela_img_base64,
        
        # نحتاج الأصل ليكون في التقرير
        'original_img_base64': base64.b64encode(image_stream.getvalue()).decode('utf-8') if image_stream else None
    }
        
    return analysis_results