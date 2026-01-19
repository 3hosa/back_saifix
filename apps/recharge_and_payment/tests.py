from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APIClient

class AlzajilViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('apps.recharge_and_payment.services.AlzajilClient')
    def test_payment_view_success(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        mock_instance.send_payment.return_value = {'RC': 0, 'MSG': 'Success', 'REF': '12345'}

        url = reverse('alzajil-payment')
        data = {
            'AC': 7100,
            'SC': 42101,
            'AMT': 100.0,
            'SNO': '777123456'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['RC'], 0)
        mock_instance.send_payment.assert_called_once()

    @patch('apps.recharge_and_payment.services.AlzajilClient')
    def test_balance_query_success(self, MockClient):
        mock_instance = MockClient.return_value
        mock_instance.query_subscriber_balance.return_value = {'RC': 0, 'MSG': 'Balance is 500'}

        url = reverse('alzajil-subscriber-balance')
        response = self.client.get(url, {'AC': 4001, 'SC': 42101, 'SNO': '777123456'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # AC is stripped from serializer validation for 'query_subscriber_balance' call arguments?
        # Serializer validates AC but service call doesn't need it passed as arg if validation is good?
        # Actually my service method signature is query_subscriber_balance(service_code, subscriber_no)
        # So AC is not passed.
        mock_instance.query_subscriber_balance.assert_called_with(service_code=42101, subscriber_no='777123456')

    @patch('apps.recharge_and_payment.services.AlzajilClient')
    def test_validation_error(self, MockClient):
        url = reverse('alzajil-payment')
        data = {
            'AC': 7100,
            # Missing SNO
            'AMT': 100.0
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('SNO', response.data)
