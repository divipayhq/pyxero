from __future__ import unicode_literals

import datetime
import json
import re
import six
import unittest
from collections import defaultdict
from mock import Mock, patch
from xml.dom.minidom import parseString

from xero.exceptions import XeroExceptionUnknown
from xero.manager import Manager


class ManagerTest(unittest.TestCase):
    def assertXMLEqual(self, xml1, xml2, message=""):
        def to_str(s):
            return s.decode("utf-8") if six.PY3 and isinstance(s, bytes) else str(s)

        def clean_xml(xml):
            xml = "<root>%s</root>" % to_str(xml)
            return str(re.sub(">\n *<", "><", parseString(xml).toxml()))

        def xml_to_dict(xml):
            nodes = re.findall("(<([^>]*)>(.*?)</\\2>)", xml)
            if len(nodes) == 0:
                return xml
            d = defaultdict(list)
            for node in nodes:
                d[node[1]].append(xml_to_dict(node[2]))
            return d

        cleaned = map(clean_xml, (xml1, xml2))
        d1, d2 = tuple(map(xml_to_dict, cleaned))

        self.assertEqual(d1, d2, message)

    def test_serializer(self):
        credentials = Mock(base_url="")
        manager = Manager("contacts", credentials)

        example_invoice_input = {
            "Date": datetime.datetime(2015, 6, 6, 16, 25, 2, 711109),
            "Reference": "ABAS 123",
            "LineItems": [
                {"Description": "Example description only"},
                {
                    "UnitAmount": "0.0000",
                    "Quantity": 1,
                    "AccountCode": "200",
                    "Description": "Example line item 2",
                    "TaxType": "OUTPUT",
                },
                {
                    "UnitAmount": "231.0000",
                    "Quantity": 1,
                    "AccountCode": "200",
                    "Description": "Example line item 3",
                    "TaxType": "OUTPUT",
                },
            ],
            "Status": "DRAFT",
            "Type": "ACCREC",
            "DueDate": datetime.datetime(2015, 7, 6, 16, 25, 2, 711136),
            "LineAmountTypes": "Exclusive",
            "Contact": {"Name": "Basket Case"},
        }
        resultant_xml = manager._prepare_data_for_save(example_invoice_input)
        resultant_xml = "<Invoice>%s</Invoice>" % resultant_xml

        expected_xml = """
        <Invoice>
          <Status>DRAFT</Status>
          <Contact>
            <Name>Basket Case</Name>
          </Contact>
          <Reference>ABAS 123</Reference>
          <Date>2015-06-06T16:25:02</Date>
          <LineAmountTypes>Exclusive</LineAmountTypes>
          <LineItems>
            <LineItem>
              <Description>Example description only</Description>
            </LineItem>
            <LineItem>
              <TaxType>OUTPUT</TaxType>
              <AccountCode>200</AccountCode>
              <UnitAmount>0.0000</UnitAmount>
              <Description>Example line item 2</Description>
              <Quantity>1</Quantity>
            </LineItem>
            <LineItem>
              <TaxType>OUTPUT</TaxType>
              <AccountCode>200</AccountCode>
              <UnitAmount>231.0000</UnitAmount>
              <Description>Example line item 3</Description>
              <Quantity>1</Quantity>
            </LineItem>
          </LineItems>
          <Type>ACCREC</Type>
          <DueDate>2015-07-06T16:25:02</DueDate>
        </Invoice>
        """

        self.assertXMLEqual(
            resultant_xml, expected_xml,
        )

    def test_serializer_phones_addresses(self):
        credentials = Mock(base_url="")
        manager = Manager("contacts", credentials)

        example_contact_input = {
            "ContactID": "565acaa9-e7f3-4fbf-80c3-16b081ddae10",
            "ContactStatus": "ACTIVE",
            "Name": "Southside Office Supplies",
            "Addresses": [{"AddressType": "POBOX"}, {"AddressType": "STREET"}],
            "Phones": [
                {"PhoneType": "DDI"},
                {"PhoneType": "DEFAULT"},
                {"PhoneType": "FAX"},
                {"PhoneType": "MOBILE"},
            ],
            "UpdatedDateUTC": datetime.datetime(2015, 9, 18, 5, 6, 56, 893),
            "IsSupplier": False,
            "IsCustomer": False,
            "HasAttachments": False,
        }
        resultant_xml = manager._prepare_data_for_save(example_contact_input)
        resultant_xml = "<Contact>%s</Contact>" % resultant_xml

        expected_xml = """
        <Contact>
          <ContactID>565acaa9-e7f3-4fbf-80c3-16b081ddae10</ContactID>
          <Name>Southside Office Supplies</Name>
          <HasAttachments>false</HasAttachments>
          <Phones>
            <Phone>
              <PhoneType>DDI</PhoneType>
            </Phone>
            <Phone>
              <PhoneType>DEFAULT</PhoneType>
            </Phone>
            <Phone>
              <PhoneType>FAX</PhoneType>
            </Phone>
            <Phone>
              <PhoneType>MOBILE</PhoneType>
            </Phone>
          </Phones>
          <IsCustomer>false</IsCustomer>
          <Addresses>
            <Address>
              <AddressType>POBOX</AddressType>
            </Address>
            <Address>
              <AddressType>STREET</AddressType>
            </Address>
          </Addresses>
          <IsSupplier>false</IsSupplier>
          <ContactStatus>ACTIVE</ContactStatus>
        </Contact>
        """

        self.assertXMLEqual(
            resultant_xml, expected_xml, "Resultant XML does not match expected."
        )

    def test_serializer_nested_singular(self):
        credentials = Mock(base_url="")
        manager = Manager("contacts", credentials)

        example_invoice_input = {
            "Date": datetime.datetime(2015, 6, 6, 16, 25, 2, 711109),
            "Reference": "ABAS 123",
            "LineItems": [{"Description": "Example description only"}],
            "Status": "DRAFT",
            "Type": "ACCREC",
            "DueDate": datetime.datetime(2015, 7, 6, 16, 25, 2, 711136),
            "LineAmountTypes": "Exclusive",
            "Contact": {"Name": "Basket Case"},
        }
        resultant_xml = manager._prepare_data_for_save(example_invoice_input)

        expected_xml = """
            <Status>DRAFT</Status>
            <Contact><Name>Basket Case</Name></Contact>
            <Reference>ABAS 123</Reference>
            <Date>2015-06-06T16:25:02</Date>
            <LineAmountTypes>Exclusive</LineAmountTypes>
            <LineItems>
              <LineItem>
                <Description>Example description only</Description>
              </LineItem>
            </LineItems>
            <Type>ACCREC</Type>
            <DueDate>2015-07-06T16:25:02</DueDate>
        """

        self.assertXMLEqual(
            resultant_xml, expected_xml,
        )

    def test_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("contacts", credentials)

        uri, params, method, body, headers, singleobject = manager._filter(
            order="LastName",
            page=2,
            offset=5,
            since=datetime.datetime(2014, 8, 10, 15, 14, 46),
            Name="John",
        )

        self.assertEqual(method, "get")
        self.assertFalse(singleobject)

        expected_params = {
            "order": "LastName",
            "page": 2,
            "offset": 5,
            "where": 'Name=="John"',
        }
        self.assertEqual(params, expected_params)

        expected_headers = {"If-Modified-Since": "2014-08-10T15:14:46"}
        self.assertEqual(headers, expected_headers)

        # Also make sure an empty call runs ok
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {})
        self.assertIsNone(headers)

        manager = Manager("invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            **{"Contact.ContactID": "3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f"}
        )

        self.assertEqual(
            params,
            {
                "where": 'Contact.ContactID==Guid("3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f")'
            },
        )

        (uri, params, method, body, headers, singleobject) = manager._filter(
            **{"AmountPaid": 0.0}
        )

        self.assertEqual(params, {"where": 'AmountPaid=="0.0"'})

    def test_filter_ids(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("contacts", credentials)

        uri, params, method, body, headers, singleobject = manager._filter(
            IDs=["1", "2", "3", "4", "5"]
        )

        self.assertEqual(method, "get")
        self.assertFalse(singleobject)

        expected_params = {
            "IDs": "1,2,3,4,5"
        }
        self.assertEqual(params, expected_params)

    def test_rawfilter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            Status="VOIDED", raw='Name.ToLower()=="test contact"'
        )
        self.assertEqual(
            params, {"where": 'Name.ToLower()=="test contact"&&Status=="VOIDED"'}
        )

    def test_boolean_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            CanApplyToRevenue=True
        )
        self.assertEqual(params, {"where": "CanApplyToRevenue==true"})

    def test_magnitude_filters(self):
        """The filter function should correctlu handle date arguments and gt, lt operators"""
        credentials = Mock(base_url="")

        manager = Manager("invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            **{"Date__gt": datetime.datetime(2007, 12, 6)}
        )

        self.assertEqual(params, {"where": "Date>DateTime(2007,12,6)"})

        manager = Manager("invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            **{"Date__lte": datetime.datetime(2007, 12, 6)}
        )

        self.assertEqual(params, {"where": "Date<=DateTime(2007,12,6)"})

    def test_unit4dps(self):
        """The manager should add a query param of unitdp iff enabled"""

        credentials = Mock(base_url="")

        # test 4dps is disabled by default
        manager = Manager("contacts", credentials)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {}, "test 4dps not enabled by default")

        # test 4dps is enabled by default
        manager = Manager("contacts", credentials, unit_price_4dps=True)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {"unitdp": 4}, "test 4dps can be enabled explicitly")

        # test 4dps can be disable explicitly
        manager = Manager("contacts", credentials, unit_price_4dps=False)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {}, "test 4dps can be disabled explicitly")

    def test_get_params(self):
        """The 'get' methods should pass GET parameters if provided.
        """

        credentials = Mock(base_url="")
        manager = Manager("reports", credentials)

        # test no parameters or headers sent by default
        uri, params, method, body, headers, singleobject = manager._get("ProfitAndLoss")
        self.assertEqual(params, {}, "test params not sent by default")

        # test params can be provided
        passed_params = {
            "fromDate": "2015-01-01",
            "toDate": "2015-01-15",
        }
        uri, params, method, body, headers, singleobject = manager._get(
            "ProfitAndLoss", params=passed_params
        )
        self.assertEqual(params, passed_params, "test params can be set")

        # test params respect, but can override, existing configuration
        manager = Manager("reports", credentials, unit_price_4dps=True)
        uri, params, method, body, headers, singleobject = manager._get(
            "ProfitAndLoss", params=passed_params
        )
        self.assertEqual(
            params,
            {"fromDate": "2015-01-01", "toDate": "2015-01-15", "unitdp": 4},
            "test params respects existing values",
        )

    def test_user_agent_inheritance(self):
        """The user_agent should be inherited from the provided credentials when not set explicitly.
        """

        # Default used when no user_agent set on manager and credentials has nothing to offer.
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("reports", credentials)
        self.assertTrue(manager.user_agent.startswith("pyxero/"))

        # Taken from credentials when no user_agent set on manager.
        credentials = Mock(base_url="", user_agent="MY_COMPANY-MY_CONSUMER_KEY")
        manager = Manager("reports", credentials)
        self.assertEqual(manager.user_agent, "MY_COMPANY-MY_CONSUMER_KEY")

        # Manager's user_agent used when explicitly set.
        credentials = Mock(base_url="", user_agent="MY_COMPANY-MY_CONSUMER_KEY")
        manager = Manager("reports", credentials, user_agent="DemoCompany-1234567890")
        self.assertEqual(manager.user_agent, "DemoCompany-1234567890")

    @patch("xero.basemanager.requests.post")
    def test_request_content_type(self, request):
        """The Content-Type should be application/xml
        """

        # Default used when no user_agent set on manager and credentials has nothing to offer.
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("reports", credentials)
        try:
            manager._get_data(lambda: ("_", {}, "post", {}, {}, True))()
        except XeroExceptionUnknown:
            pass

        call = request.mock_calls[0]
        self.assertTrue(call.kwargs["headers"]["Content-Type"], "application/xml")

    def test_request_body_format(self):
        """The body content should be in valid XML format
        """

        # Default used when no user_agent set on manager and credentials has nothing to offer.
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("reports", credentials)

        body = manager.save_or_put({"bing": "bong"})[3]

        self.assertTrue(body, "<Invoice><bing>bong</bing></Invoice>")

    def test_put_allocation(self):
        """Allocating credit should target the Allocations sub-resource
        """

        credentials = Mock(base_url="")
        manager = Manager("CreditNotes", credentials)

        uri, params, method, body, headers, singleobject = manager._put_allocation(
            "cn-1",
            {
                "AppliedAmount": "40.00",
                "Date": datetime.date(2026, 8, 26),
                "Invoice": {"InvoiceID": "inv-1"},
            },
            idempotency_key="weel-allocation-alloc-1-40.00",
        )

        self.assertEqual(uri, "/api.xro/2.0/CreditNotes/cn-1/Allocations")
        self.assertEqual(method, "put")
        self.assertEqual(params, {})
        self.assertEqual(headers, {"Idempotency-Key": "weel-allocation-alloc-1-40.00"})
        self.assertFalse(singleobject)

    def test_put_allocation_without_idempotency_key(self):
        """The idempotency key is optional
        """

        credentials = Mock(base_url="")
        manager = Manager("CreditNotes", credentials)

        headers = manager._put_allocation("cn-1", {"AppliedAmount": "40.00"})[4]

        self.assertIsNone(headers)

    def test_delete_allocation(self):
        """Removing an allocation should address it by id
        """

        credentials = Mock(base_url="")
        manager = Manager("CreditNotes", credentials)

        uri, params, method, body, headers, singleobject = manager._delete_allocation(
            "cn-1", "asp-alloc-1"
        )

        self.assertEqual(uri, "/api.xro/2.0/CreditNotes/cn-1/Allocations/asp-alloc-1")
        self.assertEqual(method, "delete")
        self.assertIsNone(body)
        self.assertIsNone(headers)

    def test_allocation_methods_are_only_on_credit_notes(self):
        """The allocation endpoints should not be decorated onto every object
        """

        credentials = Mock(base_url="")

        credit_notes = Manager("CreditNotes", credentials)
        self.assertTrue(callable(credit_notes.put_allocation))
        self.assertTrue(callable(credit_notes.delete_allocation))

        invoices = Manager("Invoices", credentials)
        self.assertFalse(hasattr(invoices, "put_allocation"))
        self.assertFalse(hasattr(invoices, "delete_allocation"))

    @patch("xero.basemanager.requests")
    def test_put_allocation_request(self, request):
        """The decorated method should assemble the whole request
        """

        credentials = Mock(base_url="https://api.xero.com", user_agent=None)
        manager = Manager("CreditNotes", credentials)
        request.put.return_value = Mock(
            status_code=200,
            headers={"content-type": "application/json"},
            text='{"Status": "OK", "CreditNotes": []}',
            content=b"",
        )

        manager.put_allocation(
            "cn-1",
            {
                "AppliedAmount": "40.00",
                "Date": datetime.date(2026, 8, 26),
                "Invoice": {"InvoiceID": "inv-1"},
            },
            idempotency_key="weel-allocation-alloc-1-40.00",
        )

        call = request.put.call_args
        self.assertEqual(
            call.args[0], "https://api.xero.com/api.xro/2.0/CreditNotes/cn-1/Allocations"
        )
        self.assertEqual(
            call.kwargs["headers"]["Idempotency-Key"], "weel-allocation-alloc-1-40.00"
        )
        self.assertXMLEqual(
            call.kwargs["data"],
            "<Allocations><Allocation>"
            "<AppliedAmount>40.00</AppliedAmount>"
            "<Date>2026-08-26T00:00:00</Date>"
            "<Invoice><InvoiceID>inv-1</InvoiceID></Invoice>"
            "</Allocation></Allocations>",
        )

    @patch("xero.basemanager.requests")
    def test_delete_allocation_request(self, request):
        """Deleting an allocation should not trip over the missing Status envelope
        """

        credentials = Mock(base_url="https://api.xero.com", user_agent=None)
        manager = Manager("CreditNotes", credentials)
        request.delete.return_value = Mock(
            status_code=200,
            headers={"content-type": "application/json"},
            text='{"AllocationID": "asp-alloc-1"}',
            content=b"",
        )

        result = manager.delete_allocation("cn-1", "asp-alloc-1")

        self.assertEqual(
            request.delete.call_args.args[0],
            "https://api.xero.com/api.xro/2.0/CreditNotes/cn-1/Allocations/asp-alloc-1",
        )
        self.assertEqual(result, {"AllocationID": "asp-alloc-1"})

    def test_idempotency_key_must_be_a_string(self):
        """A non-string idempotency key should fail before the request is made
        """

        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("CreditNotes", credentials)

        with self.assertRaises(TypeError):
            manager.put_allocation("cn-1", {"AppliedAmount": "40.00"}, 1234)

    def test_idempotency_key_length_is_checked(self):
        """An empty or over-long idempotency key should fail before the request is made
        """

        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("CreditNotes", credentials)

        for key in ("", "x" * 129):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    manager.put_allocation("cn-1", {"AppliedAmount": "40.00"}, key)

    def test_parse_api_response_without_a_status_envelope(self):
        """A response with no Status should be returned rather than raising

        Deleting an allocation answers with a bare Allocation.
        """

        credentials = Mock(base_url="")
        manager = Manager("CreditNotes", credentials)
        payload = {"AllocationID": "asp-alloc-1", "AppliedAmount": 40.0}
        response = Mock(text=json.dumps(payload))

        self.assertEqual(manager._parse_api_response(response, "CreditNotes"), payload)

    def test_parse_api_response_still_rejects_a_bad_status(self):
        """A Status that is present and not OK should still raise
        """

        credentials = Mock(base_url="")
        manager = Manager("CreditNotes", credentials)
        response = Mock(text=json.dumps({"Status": "ERROR"}))

        with self.assertRaises(AssertionError):
            manager._parse_api_response(response, "CreditNotes")
