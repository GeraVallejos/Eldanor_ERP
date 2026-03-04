def logo_upload_path(instance, filename):
    # Organiza: logos/id_empresa/nombre_archivo.png
    extension = filename.split('.')[-1]
    return f"logos/{instance.id}/logo.{extension}"