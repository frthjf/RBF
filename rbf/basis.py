''' 
This module contains the *RBF* class, which is used to symbolically 
define and numerically evaluate a radial basis function. *RBF* 
instances have been predefined in this module for some of the commonly 
used radial basis functions. The predefined radial basis functions are 
shown in the table below. For each expression in the table,
:math:`r = ||x - c||_2` and :math:`\epsilon` is a shape parameter. 
:math:`x` and :math:`c` are the evaluation points and radial basis 
function centers, respectively. The names of the predefined *RBF* 
instances are given in the abbreviation column. 

=================================  ============  =================  ======================================
Name                               Abbreviation  Positive Definite  Expression
=================================  ============  =================  ======================================
Eighth-order polyharmonic spline   phs8          No                 :math:`(\epsilon r)^8\log(\epsilon r)`
Seventh-order polyharmonic spline  phs7          No                 :math:`(\epsilon r)^7`
Sixth-order polyharmonic spline    phs6          No                 :math:`(\epsilon r)^6\log(\epsilon r)`
Fifth-order polyharmonic spline    phs5          No                 :math:`(\epsilon r)^5`
Fourth-order polyharmonic spline   phs4          No                 :math:`(\epsilon r)^4\log(\epsilon r)`
Third-order polyharmonic spline    phs3          No                 :math:`(\epsilon r)^3`
Second-order polyharmonic spline   phs2          No                 :math:`(\epsilon r)^2\log(\epsilon r)`
First-order polyharmonic spline    phs1          No                 :math:`\epsilon r`
Multiquadratic                     mq            No                 :math:`(1 + (\epsilon r)^2)^{1/2}`
Inverse multiquadratic             imq           Yes                :math:`(1 + (\epsilon r)^2)^{-1/2}`
Inverse quadratic                  iq            Yes                :math:`(1 + (\epsilon r)^2)^{-1}`
Gaussian                           ga            Yes                :math:`\exp(-(\epsilon r)^2)`
Exponential                        exp           Yes                :math:`\exp(-r/\epsilon)`
Squared Exponential                se            Yes                :math:`\exp(-r^2/(2\epsilon^2))`
Matern (v = 3/2)                   mat32         Yes                :math:`(1 + \sqrt{3} r/\epsilon)\exp(-\sqrt{3} r/\epsilon)`
Matern (v = 5/2)                   mat52         Yes                :math:`(1 + \sqrt{5} r/\epsilon + 5r^2/(3\epsilon^2))\exp(-\sqrt{5} r/\epsilon)`
=================================  ============  =================  ======================================

''' 
from __future__ import division 
from scipy.special import kv,iv
from rbf.poly import powers
import sympy 
from sympy.utilities.autowrap import ufuncify
import numpy as np 

# NO LONGER USED
# lookup table to find numerical equivalents to symbolic functions.
# This only defines functions which are not part of numpy.
_LAMBDIFY_LUT = {'besselk':kv,
                 'besseli':iv}


def _assert_shape(a,shape,label):
  ''' 
  Raises an error if *a* does not have the specified shape. If an 
  element in *shape* is *None* then that axis can have any length.
  '''
  ashape = np.shape(a)
  if len(ashape) != len(shape):
    raise ValueError(
      '*%s* is a %s dimensional array but it should be a %s dimensional array' %
      (label,len(ashape),len(shape)))

  for axis,(i,j) in enumerate(zip(ashape,shape)):
    if j is None:
      continue

    if i != j:
      raise ValueError(
        'axis %s of *%s* has length %s but it should have length %s.' %
        (axis,label,i,j))

  return
  

def _replace_nan(x):
  ''' 
  NO LONGER USED
  
  this is orders of magnitude faster than np.nan_to_num
  '''
  x[np.isnan(x)] = 0.0
  return x


def _fix_lambdified_output(fin):
  ''' 
  NO LONGER USED
  
  when lambdifying a sympy expression, the output is a scalar if the 
  expression is independent of R. This function checks the output of a 
  lambdified function and if the output is a scalar then it expands 
  the output to the proper output size. The proper output size is 
  (N,M) where N is the number of collocation points and M is the 
  number of basis functions
  '''
  def fout(*args,**kwargs):
    out = fin(*args,**kwargs)
    x = args[0]
    eps = args[-1]
    if np.isscalar(out):
      out = np.full((x.shape[0],eps.shape[0]),out,dtype=float)

    return out

  return fout  


def get_r():
  ''' 
  returns the symbolic variable for :math:`r` which is used to 
  instantiate an *RBF*
  '''
  return sympy.symbols('r')


def get_eps():
  ''' 
  returns the symbolic variable for :math:`\epsilon` which is used to 
  instantiate an *RBF*
  '''
  return sympy.symbols('eps')


# instantiate global symbolic variables _R and _EPS. Modifying these 
# variables will break this module
_R = get_r()    
_EPS = get_eps()


class RBF(object):
  ''' 
  Stores a symbolic expression of a Radial Basis Function (RBF) and 
  evaluates the expression numerically when called. 
  
  Parameters
  ----------
  expr : sympy expression
    Sympy expression for the RBF. This must be a function of the
    symbolic variable *r*, which can be obtained by calling *get_r()*
    or *sympy.symbols('r')*. *r* is the radial distance to the RBF
    center.  The expression may optionally be a function of *eps*,
    which is a shape parameter obtained by calling *get_eps()* or
    *sympy.symbols('eps')*.  If *eps* is not provided then *r* is
    substituted with *r* * *eps*.
  
  tol : float or sympy expression, optional  
    If an evaluation point, *x*, is within *tol* of an RBF center,
    *c*, then *x* is considered equal to *c*. The returned value is
    the RBF at the symbolically evaluated limit as *x* -> *c*. This is
    useful when there is a removable singularity at *c*, such as for
    polyharmonic splines. If *tol* is not provided then there will be
    no special treatment for when *x* is close to *c*. Note that
    computing the limit as *x* -> *c* can be very time intensive.
    *tol* can be a float or a sympy expression containing *eps*.

  limits : dict, optional
    Contains the limiting value of the RBF as *x* -> *c* for various
    derivative specifications. For example, *{(0,1):2*eps}* indicates
    that the limit of the derivative along the second basis direction
    in two-dimensional space is *2*eps*. If this dictionary is
    provided and *tol* is not None, then it will be searched before
    attempting to symbolically compute the limits.
    
  Examples
  --------
  Instantiate an inverse quadratic RBF

  >>> from rbf.basis import *
  >>> r = get_r()
  >>> eps = get_eps()
  >>> iq_expr = 1/(1 + (eps*r)**2)
  >>> iq = RBF(iq_expr)
  
  Evaluate an inverse quadratic at 10 points ranging from -5 to 5. 
  Note that the evaluation points and centers are two dimensional 
  arrays

  >>> x = np.linspace(-5.0,5.0,10)[:,None]
  >>> center = np.array([[0.0]])
  >>> values = iq(x,center)
    
  Instantiate a sinc RBF. This has a singularity at the RBF center and 
  it must be handled separately by specifying a number for *tol*.
  
  >>> import sympy
  >>> sinc_expr = sympy.sin(r)/r
  >>> sinc = RBF(sinc_expr) # instantiate WITHOUT specifying *tol*
  >>> x = np.array([[-1.0],[0.0],[1.0]])
  >>> c = np.array([[0.0]])
  >>> sinc(x,c) # this incorrectly evaluates to nan at the center
  array([[ 0.84147098],
         [        nan],
         [ 0.84147098]])

  >>> sinc = RBF(sinc_expr,tol=1e-10) # instantiate specifying *tol*
  >>> sinc(x,c) # this now correctly evaluates to 1.0 at the center
  array([[ 0.84147098],
         [ 1.        ],
         [ 0.84147098]])
  
  '''
  def __init__(self,expr,tol=None,limits=None):
    # make sure that *expr* does not contain any symbols other than 
    # *_R* and *_EPS*
    other_symbols = expr.free_symbols.difference({_R,_EPS})
    if len(other_symbols) != 0:
      raise ValueError(
        '*expr* cannot contain any symbols other than *r* and *eps*')
        
    if not expr.has(_R):
      raise ValueError(
        '*expr* must be a sympy expression containing the symbolic '
        'variable returned by *rbf.basis.get_r()*')
    
    if not expr.has(_EPS):
      # if eps is not in the expression then substitute eps*r for r
      expr = expr.subs(_R,_EPS*_R)
      
    if tol is not None:
      # make sure *tol* is a scalar or a sympy expression of *eps*
      tol = sympy.sympify(tol)
      other_symbols = tol.free_symbols.difference({_EPS})
      if len(other_symbols) != 0:
        raise ValueError(
          '*tol* cannot contain any symbols other than *eps*')
      
    if limits is None:
      limits = {}
      
    self.expr = expr
    self.tol = tol
    self.cache = {}
    self.limits = limits

  def __call__(self,x,c,eps=1.0,diff=None):
    ''' 
    Evaluates the RBF
    
    Parameters                                       
    ----------                                         
    x : (N,D) float array 
      evaluation points
                                                                       
    c : (M,D) float array 
      RBF centers 
        
    eps : float or (M,) float array, optional
      shape parameters for each RBF. Defaults to 1.0
                                                                           
    diff : (D,) int array, optional
      Tuple indicating the derivative order for each spatial 
      dimension. For example, if there are three spatial dimensions 
      then providing (2,0,1) would return the RBF after 
      differentiating it twice along the first axis and once along the 
      third axis.

    Returns
    -------
    out : (N,M) float array
      Returns the RBFs with centers *c* evaluated at *x*

    Notes
    -----
    1. This function evaluates the RBF derivatives symbolically, if a 
    derivative was specified, and then the symbolic expression is 
    converted to a numerical function. The numerical function is 
    cached and then reused when this function is called again with the 
    same derivative specification.

    '''
    x = np.asarray(x,dtype=float)
    _assert_shape(x,(None,None),'x')
    c = np.asarray(c,dtype=float)
    _assert_shape(c,(None,x.shape[1]),'c')

    if np.isscalar(eps):
      # makes eps an array of constant values
      eps = np.full(c.shape[0],eps,dtype=float)

    else:  
      eps = np.asarray(eps,dtype=float)

    _assert_shape(eps,(c.shape[0],),'eps')

    if diff is None:
      diff = (0,)*x.shape[1]

    else:
      # make sure diff is immutable
      diff = tuple(diff)
    
    _assert_shape(diff,(x.shape[1],),'diff')
    # expand to allow for broadcasting
    x = x.T[:,:,None] 
    c = c.T[:,None,:]
    # add function to cache if not already
    if diff not in self.cache:
      self.add_diff_to_cache(diff)
 
    args = (tuple(x)+tuple(c)+(eps,))
    out = self.cache[diff](*args)
    return out

  def __repr__(self):
    out = '<RBF : %s>' % str(self.expr)
    return out
     
  def add_diff_to_cache(self,diff):
    '''     
    Symbolically evaluates the specified derivative and then compiles 
    it to a function which can be evaluated numerically. The numerical 
    function is cached for later use. It is not necessary to use this 
    method directly because it is called as needed by the *__call__* 
    method.
    
    Parameters
    ----------
    diff : (D,) int array
      Derivative specification
        
    '''   
    diff = tuple(diff)
    _assert_shape(diff,(None,),'diff')

    dim = len(diff)
    c_sym = sympy.symbols('c:%s' % dim)
    x_sym = sympy.symbols('x:%s' % dim)    
    r_sym = sympy.sqrt(sum((xi-ci)**2 for xi,ci in zip(x_sym,c_sym)))
    # differentiate the RBF 
    expr = self.expr.subs(_R,r_sym)            
    for xi,order in zip(x_sym,diff):
      if order == 0:
        continue

      expr = expr.diff(*(xi,)*order)

    if self.tol is not None:
      if diff in self.limits:
        # use a user-specified limit if available      
        lim = self.limits[diff]
      
      else:  
        # Symbolically find the limit of the differentiated expression
        # as x->c. NOTE: this finds the limit from only one direction
        # and the limit may change when using a different direction.
        lim = expr
        for xi,ci in zip(x_sym,c_sym):
          lim = lim.limit(xi,ci)

      # create a piecewise symbolic function which is center_expr when 
      # _R<tol and expr otherwise
      expr = sympy.Piecewise((lim,r_sym<self.tol),(expr,True)) 
      
    func = ufuncify(x_sym+c_sym+(_EPS,),expr)
    self.cache[diff] = func
    

# Instantiate some common RBFs
phs8 = RBF((_EPS*_R)**8*sympy.log(_EPS*_R))
phs6 = RBF((_EPS*_R)**6*sympy.log(_EPS*_R))
phs4 = RBF((_EPS*_R)**4*sympy.log(_EPS*_R))
phs2 = RBF((_EPS*_R)**2*sympy.log(_EPS*_R))
phs7 = RBF((_EPS*_R)**7)
phs5 = RBF((_EPS*_R)**5)
phs3 = RBF((_EPS*_R)**3)
phs1 = RBF(_EPS*_R)
imq = RBF(1/sympy.sqrt(1+(_EPS*_R)**2))
iq = RBF(1/(1+(_EPS*_R)**2))
ga = RBF(sympy.exp(-(_EPS*_R)**2))
mq = RBF(sympy.sqrt(1 + (_EPS*_R)**2))
exp = RBF(sympy.exp(-_R/_EPS))
se = RBF(sympy.exp(-_R**2/(2*_EPS**2)))
mat32 = RBF((1 + sympy.sqrt(3)*_R/_EPS)*sympy.exp(-sympy.sqrt(3)*_R/_EPS))
mat52 = RBF((1 + sympy.sqrt(5)*_R/_EPS + 5*_R**2/(3*_EPS**2))*sympy.exp(-sympy.sqrt(5)*_R/_EPS))

# set some known limits so that sympy does not need to compute them
phs1.tol = 1e-10
for i in powers(0,1): phs1.limits[tuple(i)] = 0
for i in powers(0,2): phs1.limits[tuple(i)] = 0
for i in powers(0,3): phs1.limits[tuple(i)] = 0

phs2.tol = 1e-10
for i in powers(1,1): phs2.limits[tuple(i)] = 0
for i in powers(1,2): phs2.limits[tuple(i)] = 0
for i in powers(1,3): phs2.limits[tuple(i)] = 0

phs3.tol = 1e-10
for i in powers(2,1): phs3.limits[tuple(i)] = 0
for i in powers(2,2): phs3.limits[tuple(i)] = 0
for i in powers(2,3): phs3.limits[tuple(i)] = 0

phs4.tol = 1e-10
for i in powers(3,1): phs4.limits[tuple(i)] = 0
for i in powers(3,2): phs4.limits[tuple(i)] = 0
for i in powers(3,3): phs4.limits[tuple(i)] = 0

phs5.tol = 1e-10
for i in powers(4,1): phs5.limits[tuple(i)] = 0
for i in powers(4,2): phs5.limits[tuple(i)] = 0
for i in powers(4,3): phs5.limits[tuple(i)] = 0

phs6.tol = 1e-10
for i in powers(5,1): phs6.limits[tuple(i)] = 0
for i in powers(5,2): phs6.limits[tuple(i)] = 0
for i in powers(5,3): phs6.limits[tuple(i)] = 0

phs7.tol = 1e-10
for i in powers(6,1): phs7.limits[tuple(i)] = 0
for i in powers(6,2): phs7.limits[tuple(i)] = 0
for i in powers(6,3): phs7.limits[tuple(i)] = 0

phs8.tol = 1e-10
for i in powers(7,1): phs8.limits[tuple(i)] = 0
for i in powers(7,2): phs8.limits[tuple(i)] = 0
for i in powers(7,3): phs8.limits[tuple(i)] = 0

mat32.tol = 1e-10*_EPS
mat32.limits = {(0,):1, (1,):0, (2,):-3/_EPS**2,
                (0,0):1, (1,0):0, (0,1):0, (2,0):-3/_EPS**2, (0,2):-3/_EPS**2, (1,1):0}

mat52.tol = 1e-10*_EPS
mat52.limits = {(0,):1, (1,):0, (2,):-5/(3*_EPS**2), (3,):0, (4,):25/_EPS**4,
                (0,0):1, (1,0):0, (0,1):0, (2,0):-5/(3*_EPS**2), (0,2):-5/(3*_EPS**2), (1,1):0}
                     
