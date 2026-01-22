import requests
import json
from django.conf import settings

class AlzajilClient:
    """
    عميل للتفاعل مع واجهة برمجة تطبيقات الزاجل (Alzajil Utility Payment Service).
    بناءً على وثائق 'alzajil (Utility Payment Service) v1.12'.
    """

    def __init__(self):
        # الإعدادات الأساسية والروابط
        self.payment_url = getattr(settings, 'ALZAJIL_PAYMENT_URL', 'https://alzajilonline.com:8448/api/tp/v1')
        self.report_url = getattr(settings, 'ALZAJIL_REPORT_URL', 'https://alzajilonline.com:8444/api/tp/v1')
        
        self.username = getattr(settings, 'ALZAJIL_USERNAME', '')
        self.security_token = getattr(settings, 'ALZAJIL_TOKEN', '')
        self.agent_user_id = getattr(settings, 'ALZAJIL_AGENT_USER_ID', '')
        
        # إعدادات التقارير
        self.report_username = getattr(settings, 'ALZAJIL_REPORT_USERNAME', '')
        self.report_password = getattr(settings, 'ALZAJIL_REPORT_PASSWORD', '')

    def _get_credentials(self, use_report=False):
        """
        إرجاع بيانات الاعتماد المناسبة بناءً على نوع الطلب.
        """
        if use_report:
            return self.report_username, self.report_password
        return self.agent_user_id, self.security_token

    def _send_request(self, params, method='GET', body=None, use_report=False):
        """
        دالة مساعدة لإرسال الطلبات إلى API.
        """
        # تحديد الرابط المناسب
        url = self.report_url if use_report else self.payment_url

        # جلب بيانات الاعتماد الصحيحة
        usr, tkn = self._get_credentials(use_report=use_report)

        # إضافة المعاملات المشتركة
        if usr and 'USR' not in params:
            params['USR'] = usr
        if tkn and 'TKN' not in params:
            params['TKN'] = tkn

        try:
            if method.upper() == 'POST':
                response = requests.post(url, json=body, params=params, verify=False, timeout=30)
            else:
                response = requests.get(url, params=params, verify=False, timeout=30)
            
            # محاولة قراءة الاستجابة حتى لو كان الـ status code غير ناجح
            try:
                response_json = response.json()
                return response_json
            except:
                return {
                    'RC': response.status_code,
                    'MSG': f'استجابة غير معالجة من السيرفر: {response.text[:200]}'
                }
        except requests.exceptions.RequestException as e:
            # معالجة أخطاء الاتصال
            return {
                'RC': -100, # استخدام -100 كرمز خطأ عام للخدمة
                'MSG': f'خطأ في الاتصال: {str(e)}'
            }
        except json.JSONDecodeError:
             return {
                'RC': -1,
                'MSG': 'استجابة JSON غير صالحة من المزود'
            }

    def send_payment(self, data):
        """
        AC: 7100 (سداد)، 7200 (عروض)، 7600 (جملة)، 7700 (ترفيه)
        """
        # عمليات السداد تستخدم دائماً الحساب الأساسي
        return self._send_request(params={}, method='POST', body=data, use_report=False)

    def query_subscriber_balance(self, service_code, subscriber_no):
        """
        AC: 4001 (الاستعلام عن رصيد المشترك)
        الطريقة: GET
        معاملات الاستعلام: AC, SC, SNO, USR, TKN
        """
        params = {
            'AC': 4001,
            'SC': service_code,
            'SNO': subscriber_no,
            # سيتم إضافة USR و TKN تلقائياً في _send_request
        }
        # الاستعلام عن رصيد المشترك يستخدم حساب التقارير بناءً على تجربة المستخدم الناجحة
        return self._send_request(params=params, method='GET', use_report=True)

    def manage_offers(self, action_code, service_code, subscriber_no, offer_id=None):
        """
        AC: 4002-4007 (إدارة العروض)
        """
        params = {
            'AC': action_code,
            'SC': service_code,
            'SNO': subscriber_no,
        }
        if offer_id:
            params['SAC'] = offer_id
            
        # إدارة العروض (مثل جلب الباقات AC=4005) تستخدم حساب التقارير
        return self._send_request(params=params, method='GET', use_report=True)

    def query_agent_balance(self):
        """
        AC: 7400 (الاستعلام عن رصيد الوكيل)
        """
        params = {
            'AC': 7400,
        }
        return self._send_request(params=params, method='GET', use_report=False)

    def check_transaction_status(self, trans_ref):
        """
        AC: 1003 (التحقق من حالة المعاملة)
        """
        params = {
            'AC': 1003,
            'REF': trans_ref,
        }
        return self._send_request(params=params, method='GET', use_report=False)
