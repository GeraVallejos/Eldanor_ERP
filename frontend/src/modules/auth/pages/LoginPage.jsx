import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import {
    AlertCircle,
    Compass,
    Eye,
    EyeOff,
    Leaf,
    Loader2,
    Lock,
    Mail,
    ShieldCheck,
} from 'lucide-react'
import {
    clearAuthError,
    login,
    selectAuthError,
    selectAuthStatus,
} from '@/modules/auth/authSlice'

const loginSchema = z.object({
    email: z.string().trim().min(1, 'El email es requerido.').email('Formato de email inválido.'),
    password: z.string().min(1, 'La contraseña es requerida.'),
})

function LoginPage() {
    const dispatch = useDispatch()
    const navigate = useNavigate()
    const location = useLocation()
    const [showPassword, setShowPassword] = useState(false)
    const authStatus = useSelector(selectAuthStatus)
    const authError = useSelector(selectAuthError)
    const isSubmitting = authStatus === 'loading'

    useEffect(() => {
        if (!authError) {
            return
        }

        const timeoutId = setTimeout(() => {
            dispatch(clearAuthError())
        }, 4500)

        return () => clearTimeout(timeoutId)
    }, [authError, dispatch])

    const {
        register,
        handleSubmit,
        clearErrors,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(loginSchema),
        defaultValues: { email: '', password: '' },
    })

    const onSubmit = async (values) => {
        try {
            await dispatch(login(values)).unwrap()

            const nextPath = location.state?.from?.pathname || '/productos'
            navigate(nextPath, { replace: true })
        } catch {
            // El error de autenticación se muestra desde Redux state.
        }
    }

    return (
        <div className="min-h-screen w-full flex flex-col items-center justify-center bg-[#f4f7f4] font-sans text-emerald-950 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-full h-2 bg-linear-to-r from-emerald-800 via-emerald-600 to-amber-200"></div>
            <div className="absolute -top-[10%] -left-[5%] w-[60%] h-[60%] rounded-full bg-emerald-100/40 blur-[150px]"></div>
            <div className="absolute -bottom-[10%] -right-[5%] w-[60%] h-[60%] rounded-full bg-amber-50/50 blur-[150px]"></div>
            <div className="w-full max-w-137.5 px-8 z-10 py-12">
                <div className="mb-12 text-center">
                    <div className="mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-900 text-amber-200 shadow-2xl shadow-emerald-900/20 ring-4 ring-white border border-amber-200/30">
                        <Leaf size={40} strokeWidth={1.5} />
                    </div>
                    <h1 className="text-4xl font-serif font-bold tracking-tight text-emerald-900 mb-2">
                        Eldanor ERP
                    </h1>
                    <p className="text-emerald-800/70 font-medium text-base tracking-[0.2em]">
                        GESTION EMPRESARIAL
                    </p>
                </div>
                <div className="rounded-[3rem] border border-white/60 bg-white/70 backdrop-blur-2xl p-12 shadow-[0_30px_70px_rgba(2,44,34,0.12)] ring-1 ring-emerald-900/5">
                    <form className="space-y-8" onSubmit={handleSubmit(onSubmit)}>

                        {/* Mensaje de Error de Autenticación */}
                        {authError && (
                            <div className="flex items-center gap-3 py-2 px-4 rounded-lg bg-red-50/80 border border-red-100 text-red-800 animate-in fade-in slide-in-from-top-2 duration-300">
                                <AlertCircle size={18} className="shrink-0 text-red-600" />
                                <p className="text-xs font-medium leading-tight">{authError}</p>
                            </div>
                        )}

                        {/* Campo Email */}
                        <div className="space-y-3">
                            <label className="text-xs font-black text-emerald-900 uppercase tracking-[0.25em] ml-2" htmlFor="email">
                                correo
                            </label>
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 flex items-center pl-5 text-emerald-700/50 group-focus-within:text-emerald-700 transition-colors">
                                    <Mail size={22} />
                                </div>
                                <input
                                    id="email"
                                    type="email"
                                    placeholder="nombre@correo.com"
                                    className={`w-full rounded-4xl border bg-white/40 pl-14 pr-6 py-4.5 text-base transition-all focus:outline-none focus:ring-8 ${errors.email
                                            ? 'border-red-200 focus:ring-red-50/50 focus:border-red-400'
                                            : 'border-emerald-100 focus:border-emerald-600 focus:ring-emerald-50/50'
                                        }`}
                                    {...register('email', {
                                        onChange: () => {
                                            clearErrors('email')
                                            dispatch(clearAuthError())
                                        },
                                    })}
                                />
                            </div>
                            {errors.email && (
                                <p className="text-xs font-bold text-red-600 mt-2 ml-2">
                                    {errors.email.message}
                                </p>
                            )}
                        </div>

                        {/* Campo Password */}
                        <div className="space-y-3">
                            <div className="flex items-center justify-between ml-2">
                                <label className="text-xs font-black text-emerald-900 uppercase tracking-[0.25em]" htmlFor="password">
                                    contraseña
                                </label>
                                <button type="button" className="text-xs font-bold text-emerald-700 hover:text-emerald-900 transition-colors underline underline-offset-4">
                                    Recuperar acceso
                                </button>
                            </div>
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 flex items-center pl-5 text-emerald-700/50 group-focus-within:text-emerald-700 transition-colors">
                                    <Lock size={22} />
                                </div>
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="Contraseña"
                                    className={`w-full rounded-4xl border bg-white/40 pl-14 pr-14 py-4.5 text-base transition-all focus:outline-none focus:ring-8 ${errors.password
                                            ? 'border-red-200 focus:ring-red-50/50 focus:border-red-400'
                                            : 'border-emerald-100 focus:border-emerald-600 focus:ring-emerald-50/50'
                                        }`}
                                    {...register('password', {
                                        onChange: () => {
                                            clearErrors('password')
                                            dispatch(clearAuthError())
                                        },
                                    })}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute inset-y-0 right-0 flex items-center pr-5 text-emerald-700/40 hover:text-emerald-700 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                                </button>
                            </div>
                            {errors.password && (
                                <p className="text-xs font-bold text-red-600 mt-2 ml-2">
                                    {errors.password.message}
                                </p>
                            )}
                        </div>

                        {/* Botón de Envío */}
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="group relative w-full overflow-hidden rounded-4xl bg-emerald-900 px-6 py-5 text-sm font-bold text-amber-100 transition-all hover:bg-emerald-800 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70 shadow-2xl shadow-emerald-900/30"
                        >
                            <div className="flex items-center justify-center gap-3 tracking-[0.3em] uppercase text-xs">
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="h-5 w-5 animate-spin text-amber-200" />
                                        <span>Conectando con el Consejo...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>Ingresar</span>
                                        <Compass className="h-5 w-5 transition-transform group-hover:rotate-45" />
                                    </>
                                )}
                            </div>
                        </button>
                    </form>

                    {/* Divisor Visual */}
                    <div className="mt-12 pt-8 border-t border-emerald-50 text-center flex items-center justify-center gap-3">
                        <ShieldCheck size={18} className="text-emerald-800/40" />
                        <span className="text-xs font-bold text-emerald-800/30 uppercase tracking-[6px]">
                            ACCESO SEGURO
                        </span>
                    </div>
                </div>

                {/* Footer info */}
                <div className="mt-12 flex flex-col gap-8 text-center">
                    <div className="flex items-center justify-center gap-12 text-xs text-emerald-800/40 font-black uppercase tracking-[0.2em]">
                        <span className="hover:text-emerald-900 transition-colors">Ayuda</span>
                        <span className="hover:text-emerald-900 transition-colors">Protocolos</span>
                        <span className="hover:text-emerald-900 transition-colors">Seguridad</span>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default LoginPage