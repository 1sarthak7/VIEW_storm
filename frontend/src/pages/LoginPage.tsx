import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, User as UserIcon, AlertCircle, KeyRound, Sparkles, Mail } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { request } from '../api/client';

interface BootstrapStatus {
  bootstrap_required: boolean;
  message: string;
}

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [isBootstrapMode, setIsBootstrapMode] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [bootstrapToken, setBootstrapToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if system requires initial bootstrap
  const { data: bootstrapStatus } = useQuery<BootstrapStatus>({
    queryKey: ['bootstrapStatus'],
    queryFn: () => request<BootstrapStatus>('/api/v1/auth/bootstrap/status'),
  });

  const isBootstrapPending = bootstrapStatus?.bootstrap_required || false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setIsSubmitting(true);

    try {
      if (isBootstrapMode || isBootstrapPending) {
        // Execute one-time administrative bootstrap
        await request('/api/v1/auth/bootstrap', {
          method: 'POST',
          body: JSON.stringify({
            bootstrap_token: bootstrapToken.trim(),
            username: username.trim(),
            email: email.trim(),
            password: password,
          }),
        });

        setSuccessMsg('Root administrator provisioned successfully. Logging in...');
        // Automatically login with newly created credentials
        await login(username.trim(), password);
        navigate('/');
      } else {
        // Standard operator authentication
        await login(username.trim(), password);
        navigate('/');
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 bg-[#111827] border border-[#1F2937] p-8 rounded-2xl shadow-2xl relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-40 h-40 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="text-center">
          <div className="w-14 h-14 bg-indigo-600/20 border border-indigo-500/30 rounded-2xl flex items-center justify-center mx-auto text-indigo-400 mb-4 shadow-lg shadow-indigo-950">
            {isBootstrapMode || isBootstrapPending ? (
              <Sparkles className="w-8 h-8 text-amber-400" />
            ) : (
              <ShieldCheck className="w-8 h-8" />
            )}
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            {isBootstrapMode || isBootstrapPending ? 'Initial System Bootstrap' : 'Operator Sign In'}
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            {isBootstrapMode || isBootstrapPending
              ? 'Provision root administrator account using one-time bootstrap secret'
              : 'Authenticate to manage simulation runs and cluster infrastructure'}
          </p>
        </div>

        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-3 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-start gap-3 text-emerald-300 text-xs">
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {(isBootstrapMode || isBootstrapPending) && (
            <div>
              <label className="block text-xs font-medium text-amber-300 mb-1.5">
                One-Time Bootstrap Secret Token
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-amber-500 absolute left-3 top-3" />
                <input
                  type="password"
                  value={bootstrapToken}
                  onChange={(e) => setBootstrapToken(e.target.value)}
                  required
                  className="w-full bg-[#0E131F] border border-amber-500/40 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-400 transition"
                  placeholder="Enter token from backend startup log"
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Generated upon initial unprovisioned cluster start (.viewstorm_bootstrap.token).
              </p>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Operator Username
            </label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                placeholder="e.g. admin"
              />
            </div>
          </div>

          {(isBootstrapMode || isBootstrapPending) && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Administrator Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                  placeholder="admin@organization.internal"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              {isBootstrapMode || isBootstrapPending ? 'New Administrator Password' : 'Password'}
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={isBootstrapMode || isBootstrapPending ? 10 : 6}
                className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full py-2.5 px-4 font-medium text-sm rounded-lg shadow-lg transition duration-200 disabled:opacity-50 mt-2 flex items-center justify-center gap-2 text-white ${
              isBootstrapMode || isBootstrapPending
                ? 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/30'
                : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/30'
            }`}
          >
            <KeyRound className="w-4 h-4" />
            <span>
              {isSubmitting
                ? 'Processing...'
                : isBootstrapMode || isBootstrapPending
                ? 'Bootstrap Root Administrator'
                : 'Sign In as Operator'}
            </span>
          </button>
        </form>

        {/* Security Notice */}
        <div className="border-t border-[#1F2937] pt-4 mt-4">
          <div className="bg-[#0E131F] p-3 rounded-xl border border-[#1F2937] text-xs text-slate-400 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="w-2 h-2 rounded-full bg-indigo-400" />
              RBAC Protected Console
            </span>
            {isBootstrapPending && !isBootstrapMode && (
              <button
                type="button"
                onClick={() => setIsBootstrapMode(true)}
                className="text-amber-400 hover:underline font-medium text-[11px]"
              >
                Setup Admin Account
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
