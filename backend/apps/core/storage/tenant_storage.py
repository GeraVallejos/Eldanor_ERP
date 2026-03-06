from storages.backends.s3boto3 import S3Boto3Storage
from apps.core.tenant import get_current_empresa


class TenantStorage(S3Boto3Storage):

    def generate_filename(self, filename):
        empresa = get_current_empresa()

        if not empresa:
            return filename

        return f"{empresa.id}/{filename}"