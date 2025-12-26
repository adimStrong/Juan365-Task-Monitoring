from django.core.management.base import BaseCommand
from api.models import Product


class Command(BaseCommand):
    help = 'Update products list with required Juan365 products'

    PRODUCTS = [
        {'name': 'Juan365', 'description': 'Main Juan365 platform'},
        {'name': 'Juan365 Studios', 'description': 'Juan365 Studios production'},
        {'name': 'Juan365 Livestream', 'description': 'Juan365 Livestream services'},
        {'name': 'Juan365 Cares', 'description': 'Juan365 Cares CSR initiatives'},
        {'name': 'Juan365 Careers', 'description': 'Juan365 Careers recruitment'},
        {'name': 'JuanBingo', 'description': 'JuanBingo gaming platform'},
        {'name': 'JuanSports', 'description': 'JuanSports sports betting'},
        {'name': '759 Gaming', 'description': '759 Gaming platform'},
    ]

    def handle(self, *args, **options):
        self.stdout.write('Updating products...\n')

        created_count = 0
        updated_count = 0

        for product_data in self.PRODUCTS:
            product, created = Product.objects.update_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {product.name}')
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {product.name}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created: {created_count}, Updated: {updated_count}'
        ))
