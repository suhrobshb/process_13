/**
 * Registration Form Component
 * ===========================
 * 
 * User registration form with validation and security features
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useLocation } from 'wouter';
import {
  Eye,
  EyeOff,
  Mail,
  Lock,
  User,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  Github,
  Chrome,
  Shield,
  Check,
  X,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { toast } from '@/components/ui/use-toast';
import { useAuth, RegisterData } from '@/contexts/AuthContext';

// =============================================================================
// Password Strength Calculation
// =============================================================================

interface PasswordStrength {
  score: number;
  label: string;
  color: string;
  requirements: {
    length: boolean;
    uppercase: boolean;
    lowercase: boolean;
    numbers: boolean;
    symbols: boolean;
  };
}

const calculatePasswordStrength = (password: string): PasswordStrength => {
  const requirements = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    numbers: /\d/.test(password),
    symbols: /[!@#$%^&*(),.?\":{}|<>]/.test(password),
  };

  const score = Object.values(requirements).filter(Boolean).length;
  
  let label = 'Very Weak';
  let color = 'bg-red-500';
  
  if (score >= 5) {
    label = 'Very Strong';
    color = 'bg-green-500';
  } else if (score >= 4) {
    label = 'Strong';
    color = 'bg-blue-500';
  } else if (score >= 3) {
    label = 'Moderate';
    color = 'bg-yellow-500';
  } else if (score >= 2) {
    label = 'Weak';
    color = 'bg-orange-500';
  }

  return { score, label, color, requirements };
};

// =============================================================================
// Form Validation
// =============================================================================

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  name?: string;
  terms?: string;
  general?: string;
}

const validateForm = (data: RegisterData & { terms: boolean }): FormErrors => {
  const errors: FormErrors = {};

  if (!data.name) {
    errors.name = 'Name is required';
  } else if (data.name.length < 2) {
    errors.name = 'Name must be at least 2 characters';
  } else if (data.name.length > 50) {
    errors.name = 'Name must be less than 50 characters';
  }

  if (!data.email) {
    errors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    errors.email = 'Please enter a valid email address';
  }

  if (!data.password) {
    errors.password = 'Password is required';
  } else {
    const strength = calculatePasswordStrength(data.password);
    if (strength.score < 3) {
      errors.password = 'Password is too weak. Please choose a stronger password.';
    }
  }

  if (!data.confirmPassword) {
    errors.confirmPassword = 'Please confirm your password';
  } else if (data.password !== data.confirmPassword) {
    errors.confirmPassword = 'Passwords do not match';
  }

  if (!data.terms) {
    errors.terms = 'You must agree to the terms and conditions';
  }

  return errors;
};

// =============================================================================
// Password Strength Indicator
// =============================================================================

const PasswordStrengthIndicator: React.FC<{ password: string }> = ({ password }) => {
  const strength = calculatePasswordStrength(password);
  const progressValue = (strength.score / 5) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-600">Password strength</span>
        <span className={cn("text-xs font-medium", {
          'text-red-500': strength.score < 2,
          'text-orange-500': strength.score === 2,
          'text-yellow-500': strength.score === 3,
          'text-blue-500': strength.score === 4,
          'text-green-500': strength.score === 5,
        })}>
          {strength.label}
        </span>
      </div>
      <Progress value={progressValue} className="h-2" />
      <div className="grid grid-cols-2 gap-1 text-xs">
        <div className="flex items-center">
          {strength.requirements.length ? (
            <Check className="h-3 w-3 text-green-500 mr-1" />
          ) : (
            <X className="h-3 w-3 text-red-500 mr-1" />
          )}
          <span className={strength.requirements.length ? 'text-green-600' : 'text-red-600'}>
            8+ characters
          </span>
        </div>
        <div className="flex items-center">
          {strength.requirements.uppercase ? (
            <Check className="h-3 w-3 text-green-500 mr-1" />
          ) : (
            <X className="h-3 w-3 text-red-500 mr-1" />
          )}
          <span className={strength.requirements.uppercase ? 'text-green-600' : 'text-red-600'}>
            Uppercase
          </span>
        </div>
        <div className="flex items-center">
          {strength.requirements.lowercase ? (
            <Check className="h-3 w-3 text-green-500 mr-1" />
          ) : (
            <X className="h-3 w-3 text-red-500 mr-1" />
          )}
          <span className={strength.requirements.lowercase ? 'text-green-600' : 'text-red-600'}>
            Lowercase
          </span>
        </div>
        <div className="flex items-center">
          {strength.requirements.numbers ? (
            <Check className="h-3 w-3 text-green-500 mr-1" />
          ) : (
            <X className="h-3 w-3 text-red-500 mr-1" />
          )}
          <span className={strength.requirements.numbers ? 'text-green-600' : 'text-red-600'}>
            Numbers
          </span>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// Register Form Component
// =============================================================================

export const RegisterForm: React.FC = () => {
  const [, setLocation] = useLocation();
  const { register, isLoading } = useAuth();
  
  const [formData, setFormData] = useState<RegisterData & { terms: boolean }>({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    terms: false,
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (field: keyof (RegisterData & { terms: boolean }), value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear field error when user starts typing
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validationErrors = validateForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      const registerData: RegisterData = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
        confirmPassword: formData.confirmPassword,
      };

      await register(registerData);
      
      toast({
        title: "Registration Successful!",
        description: "Your account has been created successfully.",
      });
      
      // Redirect to dashboard
      setLocation('/');
    } catch (error: any) {
      console.error('Registration failed:', error);
      
      let errorMessage = 'An unexpected error occurred. Please try again.';
      
      if (error.message?.includes('Email already exists')) {
        errorMessage = 'An account with this email already exists. Please use a different email.';
        setErrors({ email: errorMessage });
      } else if (error.message?.includes('Weak password')) {
        errorMessage = 'Password is too weak. Please choose a stronger password.';
        setErrors({ password: errorMessage });
      } else if (error.message?.includes('Invalid email')) {
        errorMessage = 'Please enter a valid email address.';
        setErrors({ email: errorMessage });
      } else if (error.message?.includes('Network')) {
        errorMessage = 'Network error. Please check your connection.';
      }
      
      setErrors({ general: errorMessage });
      
      toast({
        title: "Registration Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSocialLogin = async (provider: 'github' | 'google') => {
    try {
      // Redirect to OAuth provider
      window.location.href = `/api/auth/${provider}`;
    } catch (error) {
      toast({
        title: "Social Login Failed",
        description: `Failed to login with ${provider}. Please try again.`,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="shadow-xl border-0">
          <CardHeader className="text-center space-y-4">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto">
              <Shield className="h-8 w-8 text-white" />
            </div>
            <div>
              <CardTitle className="text-2xl font-bold text-gray-900">
                Create your account
              </CardTitle>
              <CardDescription className="text-gray-600">
                Sign up to get started with AutoOps
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {errors.general && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errors.general}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    id="name"
                    type="text"
                    placeholder="Enter your full name"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    className={cn(
                      "pl-10",
                      errors.name && "border-red-500 focus:border-red-500 focus:ring-red-500"
                    )}
                    disabled={isSubmitting}
                  />
                </div>
                {errors.name && (
                  <p className="text-sm text-red-600 flex items-center">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {errors.name}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    className={cn(
                      "pl-10",
                      errors.email && "border-red-500 focus:border-red-500 focus:ring-red-500"
                    )}
                    disabled={isSubmitting}
                  />
                </div>
                {errors.email && (
                  <p className="text-sm text-red-600 flex items-center">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {errors.email}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Create a strong password"
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    className={cn(
                      "pl-10 pr-10",
                      errors.password && "border-red-500 focus:border-red-500 focus:ring-red-500"
                    )}
                    disabled={isSubmitting}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={isSubmitting}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
                {formData.password && (
                  <PasswordStrengthIndicator password={formData.password} />
                )}
                {errors.password && (
                  <p className="text-sm text-red-600 flex items-center">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {errors.password}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm your password"
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    className={cn(
                      "pl-10 pr-10",
                      errors.confirmPassword && "border-red-500 focus:border-red-500 focus:ring-red-500"
                    )}
                    disabled={isSubmitting}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    disabled={isSubmitting}
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-sm text-red-600 flex items-center">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {errors.confirmPassword}
                  </p>
                )}
              </div>

              <div className="flex items-start space-x-2">
                <input
                  id="terms"
                  type="checkbox"
                  checked={formData.terms}
                  onChange={(e) => handleInputChange('terms', e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-1"
                  disabled={isSubmitting}
                />
                <div className="text-sm">
                  <Label htmlFor="terms" className="text-gray-700">
                    I agree to the{' '}
                    <a href="/terms" className="text-blue-600 hover:text-blue-500">
                      Terms of Service
                    </a>{' '}
                    and{' '}
                    <a href="/privacy" className="text-blue-600 hover:text-blue-500">
                      Privacy Policy
                    </a>
                  </Label>
                  {errors.terms && (
                    <p className="text-sm text-red-600 flex items-center mt-1">
                      <AlertCircle className="h-3 w-3 mr-1" />
                      {errors.terms}
                    </p>
                  )}
                </div>
              </div>

              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  <>
                    Create account
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">Or continue with</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleSocialLogin('github')}
                disabled={isSubmitting}
              >
                <Github className="h-4 w-4 mr-2" />
                GitHub
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleSocialLogin('google')}
                disabled={isSubmitting}
              >
                <Chrome className="h-4 w-4 mr-2" />
                Google
              </Button>
            </div>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                Already have an account?{' '}
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setLocation('/login')}
                  className="text-blue-600 hover:text-blue-500 p-0"
                >
                  Sign in
                </Button>
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default RegisterForm;