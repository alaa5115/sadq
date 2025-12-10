import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.optimizers import Adam 
import numpy as np
from PIL import Image
import io
import cv2
import base64 
from tf_keras_vis.gradcam import Gradcam 
from tf_keras_vis.utils.model_modifiers import ReplaceToLinear 
from tf_keras_vis.utils import normalize 

# حجم الصورة الذي يتطلبه النموذج 
IMG_SIZE = 128

# =========================================================
# 1. بناء نموذج CNN المُتخصص في التحليل الجنائي
# =========================================================

def build_forensics_model():
    """بناء نموذج شبكة عصبية تلافيفية (CNN) للكشف عن التلاعب."""
    
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
    
    model.compile(optimizer=Adam(learning_rate=0.0001), 
                  loss='binary_crossentropy', 
                  metrics=['accuracy'])
    
    return model

# =========================================================
# 2. دالة تحليل الذكاء الاصطناعي الرئيسية
# =========================================================

def analyze_with_ai(image_stream, global_model, ela_weight, prnu_score):
    """
    تشغيل تحليل الذكاء الاصطناعي باستخدام النموذج المُحمّل عالمياً.
    """
    
    # تهيئة قيم الفشل
    ai_trust_score = 0.0
    gradcam_base64_image = None
    ai_msg = "❌ لم يتم إجراء تحليل الذكاء الاصطناعي."
    
    try:
        # 1. إعداد الصورة
        image_stream.seek(0)
        original_img = Image.open(image_stream).convert('RGB')
        
        # تحجيم الصورة لتناسب إدخال النموذج (128x128)
        img = original_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS)
        img_np = np.array(img, dtype=np.float32) / 255.0
        
        # إدخال النموذج: (1, 128, 128, 3)
        input_tensor = np.expand_dims(img_np, axis=0)

        # 2. التنبؤ بالنموذج
        prediction = global_model.predict(input_tensor)[0][0]
        # تحويل التنبؤ إلى درجة ثقة في الأصالة (0=مزور، 1=أصيل).
        ai_trust_score = float(prediction * 100) # 💡 الإصلاح: تحويل إلى float قياسي

        # 3. توليد خريطة Grad-CAM التفسيرية
        original_img_np = np.array(original_img.copy())
        
        try:
            # تحديد آخر طبقة تلافيفية (Conv2D) كهدف للرؤية
            candidate_layers = [layer.name for layer in global_model.layers if 'conv2d' in layer.name.lower()]
            
            if candidate_layers:
                target_layer = candidate_layers[-1] 

                # تعريف دالة الهدف لـ Grad-CAM (للكشف الثنائي)
                def loss(output):
                    # نستخدم دالة لا شيء بسيطة
                    return (output * 0) + 1 
                
                # استخدام Gradcam مع استنساخ النموذج لـ Keras-Vis
                gradcam = Gradcam(global_model, clone=True)
                                  
                # توليد خريطة Grad-CAM
                cam = gradcam(loss, input_tensor, penultimate_layer=target_layer, visualize_cam=True)
                
                # معالجة وتلوين الخريطة
                heatmap = np.uint8(cv2.resize(cam[0], (original_img.width, original_img.height), 
                                                 interpolation=cv2.INTER_LINEAR) * 255)
                
                # تحويل الصورة إلى BGR لاستخدام cv2.applyColorMap
                original_img_cv = cv2.cvtColor(original_img_np, cv2.COLOR_RGB2BGR) 
                heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
                
                # دمج الخريطة مع الصورة الأصلية
                superimposed_img = cv2.addWeighted(original_img_cv, 0.6, heatmap_colored, 0.4, 0)
                
                # التحويل إلى Base64
                heatmap_img = Image.fromarray(cv2.cvtColor(superimposed_img, cv2.COLOR_BGR2RGB))
                buffer = io.BytesIO()
                heatmap_img.save(buffer, format="PNG")
                gradcam_base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                ai_msg = f"✅ تم توليد خريطة Grad-CAM بنجاح. (درجة AI: {ai_trust_score:.2f}%)"
            else:
                raise ValueError("لم يتم العثور على طبقة Conv2D.")

        except Exception as e:
            # رسالة تخبر المستخدم بفشل Grad-CAM فقط، مع الاحتفاظ بنتيجة التنبؤ
            print(f"Error in Grad-CAM generation: {e}")
            ai_msg = f"🟡 التحليل الرقمي بالذكاء الاصطناعي نجح ({ai_trust_score:.2f}%)، لكن فشل توليد خريطة Grad-CAM التفسيرية."

            
    except Exception as e:
        # فشل حاد في أي خطوة قبل أو أثناء التنبؤ بالنموذج
        print(f"Critical error in AI analysis: {e}")
        ai_msg = f"❌ فشل حاد في التحليل بواسطة AI: {str(e)}"
        
    # 5. دمج النتائج وتقرير النتيجة النهائية
    # الوزن: 40% لـ AI، 30% لـ PRNU، 30% لـ ELA
    final_score_unclamped = (0.4 * ai_trust_score) + (0.3 * prnu_score) + (0.3 * ela_weight)
    final_score = np.clip(final_score_unclamped, 0.0, 100.0) 

    # 6. بناء رسالة التحليل النهائية
    if final_score < 50 and not "فشل حاد" in ai_msg:
        ai_msg = f"⚠️ يشتبه في التلاعب/التوليد الآلي! درجة الثقة في الأصالة: {ai_trust_score:.2f}%."
    elif final_score >= 80:
        if "فشل توليد" not in ai_msg:
             ai_msg = f"✅ موثوق به جداً! درجة الثقة في الأصالة: {ai_trust_score:.2f}%."
        # لا نغير الرسالة إذا كان هناك فشل في Grad-CAM
    elif final_score >= 50 and not "فشل حاد" in ai_msg:
        if "فشل توليد" not in ai_msg:
            ai_msg = f"🟡 درجة ثقة متوسطة في الأصالة: {ai_trust_score:.2f}%. يُنصح بمزيد من التدقيق."
        
    # 7. إرجاع النتائج
    return float(final_score), ai_msg, gradcam_base64_image, float(ai_trust_score)