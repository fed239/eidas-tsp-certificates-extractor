import argparse
import os
import requests
from lxml import etree


def main():
    # Define CLI arguments
    parser = argparse.ArgumentParser(
        description='Extracting CA certificates from the EU Trusted List for a given country and service type.'
    )
    parser.add_argument('service', choices=['QWAC', 'QSealC'], help=(
        'Type of service to retrieve certificate for. '
        'QWAC - Qualified certificate for website authentication; '
        'QSealC - Qualified certificate for electronic seal'))
    parser.add_argument('country', help='ISO 3166-1 alpha-2 country code (only EEA countries are supported)')
    parser.add_argument('--target_folder', help='Target folder to save certificate files in')
    args = parser.parse_args()

    # Define service URI based on argument
    if args.service == 'QWAC':
        service_uri = 'http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/ForWebSiteAuthentication'
    elif args.service == 'QSealC':
        service_uri = 'http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/ForeSeals'

    # Download XML file
    url = f'https://eidas.ec.europa.eu/efda/tl-browser/api/v1/browser/download/{args.country}'
    response = requests.get(url)
    xml_content = response.content

    # Parse XML and evaluate XPath expression
    root = etree.fromstring(xml_content)
    namespaces = root.nsmap
    if namespaces.get(None, None):
        namespaces['tsl'] = namespaces.pop(None)
    xpath_expr = (
        "//tsl:TSPService["
        "tsl:ServiceInformation/tsl:ServiceTypeIdentifier='http://uri.etsi.org/TrstSvc/Svctype/CA/QC' and "
        "tsl:ServiceInformation/tsl:ServiceStatus='http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted' and "
        "tsl:ServiceInformation/tsl:ServiceInformationExtensions/tsl:Extension["
        f"tsl:AdditionalServiceInformation/tsl:URI[text()='{service_uri}']]]"
    )
    elements = root.xpath(xpath_expr, namespaces=namespaces)

    # Extract X.509 certificate from found elements and write to file
    if elements:
        target_folder = args.target_folder
        os.makedirs(target_folder, exist_ok=True)
        for i, element in enumerate(elements):
            name_elem = element.find(".//tsl:ServiceName/tsl:Name", namespaces)
            print(f'Extracting: {name_elem.text}')
            cert_elem = element.find('.//tsl:X509Certificate', namespaces)
            if cert_elem is not None:
                cert_str = cert_elem.text.strip().replace(' ', '').replace('\n', '')
                wrapped_cert_str = "-----BEGIN CERTIFICATE-----\n"
                for j in range(0, len(cert_str), 64):
                    wrapped_cert_str += cert_str[j:j+64] + "\n"
                wrapped_cert_str += "-----END CERTIFICATE-----\n"
                filename = f'{args.country}_{i}.pem'
                filepath = os.path.join(target_folder, filename)
                with open(filepath, 'w') as f:
                    f.write(wrapped_cert_str)
                print(f'Wrote {filepath}')

if __name__ == '__main__':
    main()
