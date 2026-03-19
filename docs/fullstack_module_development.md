# Guia Full-Stack de Desarrollo de Modulos

Este documento describe cómo implementar un **nuevo módulo completamente** (backend Django + frontend React), manteniendo sincronización entre capas.

## Ejemplo: Crear módulo "Ventas"

### Fase 1: Planificación (Backend)

**1a. Definir modelo de negocio**
```
Entidad: Venta
- Estados: BORRADOR → CONFIRMADA → ENVIADA → ENTREGADA (o CANCELADA en cualquier punto)
- Campos principales: numero_folio, cliente, fecha, monto_total, detalle
- Items: VentaItem con producto, cantidad, precio_unitario
- Trazabilidad: Reserva stock, genera factura (via AccountingBridge)
```

**1b. Definir permisos**
```python
# backend/apps/core/permisos/constantes_permisos.py
class Modulos(str):
    VENTAS = "VENTAS"

class Acciones(str):
    VER = "VER"
    CREAR = "CREAR"
    CONFIRMAR = "CONFIRMAR"  # Nuevo para este módulo

PERMISOS_CATALOGO = {
    Modulos.VENTAS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.CONFIRMAR,
        Acciones.BORRAR,
    ]
}
```

**1c. Definir eventos que emitirá**
```
Eventos de Dominio:
- VENTA_CREADA (payload: venta_id, cliente_id)
- VENTA_CONFIRMADA (payload: venta_id, items_count, monto_total)
- VENTA_ENVIADA (payload: venta_id, factura_id)

Eventos Outbox:
- VENTA_CONFIRMADA (para notificaciones)
- VENTA_ENVIADA (para despacho/logística)
```

---

### Fase 2: Implementacion Backend

**2a. Crear estructura**
```bash
mkdir -p apps/ventas/{models,services,api,tests}
touch apps/ventas/__init__.py apps/ventas/apps.py apps/ventas/admin.py
```

**2b. Modelos** (`apps/ventas/models/__init__.py`)
```python
from django.db import models
from apps.core.models import BaseModel

class Venta(BaseModel):
    ESTADOS = [
        ("BORRADOR", "Borrador"),
        ("CONFIRMADA", "Confirmada"),
        ("ENVIADA", "Enviada"),
        ("ENTREGADA", "Entregada"),
        ("CANCELADA", "Cancelada"),
    ]
    
    numero_folio = models.CharField(max_length=20, unique_for_date="creado_en")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="BORRADOR")
    cliente = models.ForeignKey("contactos.Cliente", on_delete=models.CASCADE)
    fecha = models.DateField()
    monto_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Referencia a factura generada
    factura_documento_compra = models.ForeignKey(
        "compras.DocumentoCompraProveedor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Factura de venta generada"
    )
    
    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["empresa", "estado", "creado_en"]),
            models.Index(fields=["empresa", "cliente", "creado_en"]),
        ]

class VentaItem(BaseModel):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey("productos.Producto", on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    
    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
```

  ### 2b.1 Recomendacion de consistencia: integrar `apps/documentos`

  Si el nuevo modulo representa un **documento comercial** (cotizacion, orden, factura, guia, nota, etc.), conviene heredar las bases de `apps.documentos.models` para estandarizar estructura y comportamiento.

  Uso recomendado:

  ```python
  from apps.documentos.models import DocumentoTributableBase, DocumentoItemBase


  class Venta(DocumentoTributableBase):
    # Hereda: estado, observaciones, subtotal, total, numero, impuestos
    cliente = models.ForeignKey("contactos.Cliente", on_delete=models.PROTECT)
    fecha_emision = models.DateField()


  class VentaItem(DocumentoItemBase):
    # Hereda: producto, descripcion, cantidad, precio_unitario, impuesto, subtotal, total
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
  ```

  Checklist rapido de decision:
  - Si el modulo tiene cabecera + items + totales + impuestos, **usar `DocumentoTributableBase` y `DocumentoItemBase`**.
  - Si no tiene naturaleza documental (ej. configuraciones, catalogos, entidades maestras), usar `BaseModel` directamente.
  - Si requiere trazabilidad documental (`documento_tipo`, `documento_id`) para inventario o referencias cruzadas, usar `DocumentoReferenciaMixin` o `TipoDocumentoReferencia`.

  Estado actual del proyecto:
  - `Presupuesto` ya hereda `DocumentoBase`.
  - `OrdenCompra` hereda `DocumentoTributableBase` y `OrdenCompraItem` hereda `DocumentoItemBase`.
  - Esto confirma que `apps/documentos` **si esta en uso** y es parte de la estandarizacion del dominio.

**2c. Servicios** (`apps/ventas/services/venta_service.py`)
```python
from django.db import transaction
from apps.core.exceptions import BusinessRuleError, ResourceNotFoundError
from apps.core.services import WorkflowService, DomainEventService, OutboxService
from apps.core.services import SecuenciaService, AccountingBridge

class VentaService:
    """Servicio de logica negocio de ventas."""
    
    ESTADOS_TRANSICION = {
        "BORRADOR": ["CONFIRMADA", "CAN...]
        "CONFIRMADA": ["ENVIADA", "CANCELADA"],
        "ENVIADA": ["ENTREGADA"],
        "ENTREGADA": [],
        "CANCELADA": [],
    }
    
    @transaction.atomic
    def crear_venta(self, empresa, cliente, items_data, usuario=None):
        """
        Crea venta en estado BORRADOR.
        
        Valida cliente activo + items no vacio.
        Genera folio secuencial.
        Emite DomainEvent.
        """
        if not cliente.activo:
            raise BusinessRuleError("Cliente debe estar activo.")
        
        if not items_data:
            raise BusinessRuleError("Venta debe tener al menos un item.")
        
        # Generar folio
        numero_folio = SecuenciaService.obtener_siguiente_numero(
            empresa=empresa,
            tipo_documento="VENTA"
        )
        
        # Crear venta y items
        venta = Venta.objects.create(
            empresa=empresa,
            cliente=cliente,
            numero_folio=numero_folio,
            estado="BORRADOR",
            creado_por=usuario,
            fecha=timezone.now().date()
        )
        
        for item_data in items_data:
            VentaItem.objects.create(
                venta=venta,
                producto_id=item_data["producto_id"],
                cantidad=item_data["cantidad"],
                precio_unitario=item_data["precio_unitario"]
            )
        
        # Calcular total
        venta.monto_total = sum(item.subtotal for item in venta.items.all())
        venta.save()
        
        # Emitir evento funcional
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="Venta",
            aggregate_id=venta.id,
            event_type="VENTA_CREADA",
            payload={
                "venta_id": str(venta.id),
                "numero_folio": venta.numero_folio,
                "cliente_id": str(cliente.id),
            },
            usuario=usuario,
            idempotency_key=f"domain:venta_{venta.id}_creada"
        )
        
        return venta
    
    @transaction.atomic
    def confirmar_venta(self, empresa, venta_id, usuario=None):
        """
        Confirma venta: BORRADOR -> CONFIRMADA.
        
        Valida transicion + reserva stock.
        Emite eventos de dominio + outbox.
        Solicita factura a puente contable.
        """
        venta = Venta.objects.get(id=venta_id, empresa=empresa)
        
        # Validar transicion
        next_state = WorkflowService.assert_transition(
            venta.estado,
            "CONFIRMADA",
            self.ESTADOS_TRANSICION
        )
        
        # Reservar stock para cada item
        from apps.inventario.services import InventarioService
        for item in venta.items.all():
            InventarioService.reservar_stock(
                empresa=empresa,
                producto=item.producto,
                cantidad=item.cantidad,
                documento_ref=str(venta.id)
            )
        
        # Aplicar transicion
        venta = WorkflowService.apply_transition(
            venta,
            next_state,
            self.ESTADOS_TRANSICION
        )
        
        # Emitir evento funcional
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="Venta",
            aggregate_id=venta.id,
            event_type="VENTA_CONFIRMADA",
            payload={
                "venta_id": str(venta.id),
                "items_count": venta.items.count(),
                "monto_total": str(venta.monto_total),
            },
            usuario=usuario,
            idempotency_key=f"domain:venta_{venta.id}_confirmada"
        )
        
        # Encolar para notificaciones
        OutboxService.enqueue(
            event_type="VENTA_CONFIRMADA",
            payload={
                "venta_id": str(venta.id),
                "cliente_id": str(venta.cliente_id),
                "monto": str(venta.monto_total),
            },
            idempotency_key=f"outbox:venta_{venta.id}_notificacion",
            consumer_name="notificaciones"
        )
        
        # Solicitar factura a contabilidad (bridging)
        AccountingBridge.request_entry(
            numero_referencia=f"VENTA_{venta.numero_folio}",
            tipo_entrada="VENTA",
            conceptos=[
                {
                    "cuenta": "1101",  # Ingresos
                    "debe": float(venta.monto_total),
                    "descripcion": f"Venta {venta.numero_folio}",
                }
            ],
            meta={"venta_id": str(venta.id)}
        )
        
        return venta
```

**2d. API** (`apps/ventas/api/views.py`)
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones

class VentaViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    serializer_class = VentaSerializer
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar": Acciones.CONFIRMAR,
    }
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        venta = VentaService.crear_venta(
            empresa=self.get_empresa(),
            cliente_id=serializer.validated_data["cliente"].id,
            items_data=serializer.validated_data["items"],
            usuario=request.user
        )
        
        return Response(
            VentaSerializer(venta).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        venta = self.get_object()
        venta = VentaService.confirmar_venta(
            empresa=self.get_empresa(),
            venta_id=venta.id,
            usuario=request.user
        )
        return Response(VentaSerializer(venta).data)
```

**2e. Tests** (`apps/ventas/tests/test_api.py`)
```python
import pytest
from django.test import Client

@pytest.mark.django_db
def test_crear_venta_api(client, usuario, empresa):
    response = client.post(
        "/api/ventas/",
        {
            "cliente_id": "...",
            "items": [{"producto_id": "...", "cantidad": 1, "precio_unitario": 100}]
        },
        content_type="application/json"
    )
    
    assert response.status_code == 201
    assert response.data["estado"] == "BORRADOR"

@pytest.mark.django_db
def test_confirmar_venta_api(client, usuario, venta_borrador):
    response = client.post(f"/api/ventas/{venta_borrador.id}/confirmar/")
    
    assert response.status_code == 200
    assert response.data["estado"] == "CONFIRMADA"
```

---

### Fase 3: Implementacion Frontend

**3a. Crear estructura**
```bash
mkdir -p src/modules/ventas/{pages,components,store,tests}
touch src/modules/ventas/{pages,components,store}/index.js
```

**3b. Constants** (`src/modules/ventas/constants.js`)
```javascript
export const VENTA_ESTADOS = {
  BORRADOR: { label: "Borrador", color: "gray" },
  CONFIRMADA: { label: "Confirmada", color: "blue" },
  ENVIADA: { label: "Enviada", color: "yellow" },
  ENTREGADA: { label: "Entregada", color: "green" },
  CANCELADA: { label: "Cancelada", color: "red" },
};

export const VENTA_TRANSICIONES = {
  BORRADOR: ["CONFIRMADA", "CANCELADA"],
  CONFIRMADA: ["ENVIADA", "CANCELADA"],
  ENVIADA: ["ENTREGADA"],
  ENTREGADA: [],
  CANCELADA: [],
};

export const Modulos = {
  VENTAS: "VENTAS",
};

export const Acciones = {
  VER: "VER",
  CREAR: "CREAR",
  EDITAR: "EDITAR",
  CONFIRMAR: "CONFIRMAR",
  BORRAR: "BORRAR",
};
```

**3c. API Hooks** (`src/modules/ventas/store/api.js`)
```javascript
import { apiClient } from "@/api/client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export const useFetchVentas = (filters = {}) => {
  return useQuery({
    queryKey: ["ventas", filters],
    queryFn: async () => {
      const { data } = await apiClient.get("/api/ventas/", { params: filters });
      return data;
    },
  });
};

export const useFetchVenta = (id) => {
  return useQuery({
    queryKey: ["venta", id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/ventas/${id}/`);
      return data;
    },
    enabled: !!id,
  });
};

export const useCreateVenta = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ventaData) => {
      const { data } = await apiClient.post("/api/ventas/", ventaData);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ventas"] });
    },
  });
};

export const useConfirmarVenta = (ventaId) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post(`/api/ventas/${ventaId}/confirmar/`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["venta", ventaId] });
      queryClient.invalidateQueries({ queryKey: ["ventas"] });
    },
  });
};
```

**3d. Pages** (`src/modules/ventas/pages/ListPage.jsx`)
```jsx
import React, { useState } from "react";
import { useFetchVentas } from "../store/api";
import { useAuth } from "@/hooks/useAuth";
import { Modulos, Acciones } from "../constants";

export const VentasListPage = () => {
  const { user } = useAuth();
  const { data: ventas, isLoading, error } = useFetchVentas();
  const [filters, setFilters] = useState({});

  // Verificar permisos
  const puedeCrear = user?.tiene_permiso?.(Modulos.VENTAS, Acciones.CREAR);
  const puedeEditar = user?.tiene_permiso?.(Modulos.VENTAS, Acciones.EDITAR);
  const puedeConfirmar = user?.tiene_permiso?.(Modulos.VENTAS, Acciones.CONFIRMAR);

  if (isLoading) return <div>Cargando...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="ventas-list">
      <h1>Ventas</h1>

      {puedeCrear && (
        <button onClick={() => window.location.href = "/ventas/crear"}>
          Crear Venta
        </button>
      )}

      <table>
        <thead>
          <tr>
            <th>Folio</th>
            <th>Cliente</th>
            <th>Monto</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {ventas?.map((venta) => (
            <tr key={venta.id}>
              <td>{venta.numero_folio}</td>
              <td>{venta.cliente.nombre}</td>
              <td>${venta.monto_total}</td>
              <td>{venta.estado}</td>
              <td>
                {puedeEditar && (
                  <a href={`/ventas/${venta.id}/editar`}>Editar</a>
                )}
                {puedeConfirmar && venta.estado === "BORRADOR" && (
                  <button onClick={() => confirmarVenta(venta.id)}>
                    Confirmar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

**3e. Form Component** (`src/modules/ventas/components/VentaForm.jsx`)
```jsx
import React from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { useCreateVenta } from "../store/api";

export const VentaForm = ({ onSuccess }) => {
  const { control, handleSubmit, formState: { errors } } = useForm();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });
  const createVenta = useCreateVenta();

  const onSubmit = async (data) => {
    try {
      await createVenta.mutateAsync(data);
      onSuccess?.();
    } catch (error) {
      const detail = error.response?.data?.detail;
      const errCode = error.response?.data?.error_code;
      // Mostrar al usuario
      alert(`Error [${errCode}]: ${detail}`);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Cliente select */}
      {/* Items tabla */}
      <button type="button" onClick={() => append({})}>
        Agregar Item
      </button>

      <button type="submit" disabled={createVenta.isPending}>
        {createVenta.isPending ? "Guardando..." : "Crear Venta"}
      </button>
    </form>
  );
};
```

**3f. Tests** (`src/modules/ventas/tests/pages.test.jsx`)
```javascript
import { render, screen } from "@testing-library/react";
import { VentasListPage } from "../pages/ListPage";
import * as api from "../store/api";

jest.mock("../store/api");

describe("VentasListPage", () => {
  it("muestra tabla de ventas", async () => {
    api.useFetchVentas.mockReturnValue({
      data: [
        { id: "1", numero_folio: "SOM-001", estado: "CONFIRMADA" }
      ],
      isLoading: false,
    });

    render(<VentasListPage />);
    expect(screen.getByText("SOM-001")).toBeInTheDocument();
  });

  it("oculta botón crear si sin permiso", () => {
    const useAuth = require("@/hooks/useAuth");
    useAuth.useAuth.mockReturnValue({
      user: { tiene_permiso: () => false }
    });

    render(<VentasListPage />);
    expect(screen.queryByText("Crear Venta")).not.toBeInTheDocument();
  });
});
```

---

### Fase 4: Integración y Testing

**4a. Routing** (`frontend/src/config/router.jsx`)
```javascript
{
  path: "/ventas",
  lazy: () => import("@/modules/ventas/pages").then(m => ({
    Component: m.VentasListPage
  }))
},
{
  path: "/ventas/:id",
  lazy: () => import("@/modules/ventas/pages").then(m => ({
    Component: m.VentasDetailPage
  }))
},
{
  path: "/ventas/crear",
  lazy: () => import("@/modules/ventas/pages").then(m => ({
    Component: m.VentasFormPage
  }))
},
```

**4b. Navigation** (`frontend/src/config/navigation.js`)
```javascript
export const NAVIGATION = [
  // ... otros módulos
  {
    label: "Ventas",
    href: "/ventas",
    icon: "ShoppingCart",
    modulo: "VENTAS",
    requiredActions: ["VER"],
  },
];
```

**4c. Test end-to-end**
```bash
# Backend
pytest apps/ventas/tests/ -v

# Frontend
npm test src/modules/ventas/

# Integration
npm run test:e2e -- --spec "cypress/e2e/ventas.cy.js"
```

---

### Fase 5: Validación de Arquitectura

**Checklist final antes de mergear:**

✅ Backend:
- [ ] Excepciones: Solo `AppError` subclases en servicios
- [ ] Docstrings: Todos métodos de servicio documentados en español
- [ ] Eventos: `DomainEvent` + `OutboxEvent` emitidos correctamente
- [ ] Permisos: `permission_action_map` completo
- [ ] Tests: Servicio + API + eventos con >80% cobertura
- [ ] No hay imports DRF en `apps/ventas/services/`

✅ Frontend:
- [ ] Permisos: UI valida `user.tiene_permiso()` antes de mostrar acciones
- [ ] Errores: Muestra `detail` + `error_code` del servidor
- [ ] Estados: UI refleja transiciones válidas del backend
- [ ] Tests: Lista >80% cobertura
- [ ] Responsive: Funciona en móvil/tablet

✅ Documentación:
- [ ] README local en `apps/ventas/` explicando flujos
- [ ] Docstrings de servicio
- [ ] En `docs/` si modulo es complejo

---

## Ventajas de este enfoque

| Aspecto | Ventaja |
|--------|--------|
| **Sincronización** | Backend y frontend desarrollan juntos; cambios de API impactan UI automáticamente |
| **Reusoabilidad** | Servicios transversales (WorkflowService, DomainEventService) evitan duplicación |
| **Testing** | Ambas capas testeadas; errores detectados temprano |
| **Permisos** | UI refleja backend; no hay bypass de seguridad |
| **Auditoria** | Todos cambios registrados en AuditEvent + DomainEvent |
| **Scaling** | Nuevo modulo sigue patrón = fácil de mantener |

