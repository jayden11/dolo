import numpy

def residuals(f, g, s, x, dr, P, Q, parms):

    N = s.shape[0]
    n_s = s.shape[1]

    n_ms = P.shape[0]   # number of markov states
    n_mv = P.shape[1] # number of markov variable

    res = numpy.zeros_like(x)


    import time

    for i_ms in range(n_ms):
        # solving on grid for markov index i_ms
        # m = P[i_ms,:][None,:]
        m = numpy.tile(P[i_ms,:],(N,1))
        xm = x[i_ms,:,:]

        for I_ms in range(n_ms):

            # M = P[I_ms,:][None,:]
            M = numpy.tile(P[I_ms,:], (N,1))
            prob = Q[i_ms, I_ms]

            S = g(m, s, xm, M, parms)
            XM = dr(I_ms, S)
            rr = f(m,s,xm,M,S,XM,parms)
            res[i_ms,:,:] += prob*rr

    return res

def get_initial_guess(model):

    pass


def solve_mfg_model(model, maxit=1000, initial_guess=None, with_complementarities=True, verbose=True, orders=None, output_type='dr'):

    assert(model.model_type == 'mfga')

    [P, Q] = model.markov_chain

    n_ms = P.shape[0]   # number of markov states
    n_mv = P.shape[1] # number of markov variables

    x0 = model.calibration['controls']
    parms = model.calibration['parameters']
    n_x = len(x0)
    n_s = len(model.symbols['states'])

    approx = model.options['approximation_space']
    a = approx['a']
    b = approx['b']
    if orders is None:
        orders = approx['orders']

    from dolo.numeric.decision_rules_markov import MarkovDecisionRule

    mdr = MarkovDecisionRule(n_ms, a, b, orders)

    grid = mdr.grid
    N = grid.shape[0]



#    if isinstance(initial_guess, numpy.ndarray):
#        print("Using initial guess (1)")
#        controls = initial_guess
#    elif isinstance(initial_guess, dict):
#        print("Using initial guess (2)")
#        controls_0 = initial_guess['controls']
#        ap_space = initial_guess['approximation_space']
#        if False in (approx['orders']==orders):
#            print("Interpolating initial guess")
#            old_dr = MarkovDecisionRule(controls_0.shape[0], ap_space['smin'], ap_space['smax'], ap_space['orders'])
#            old_dr.set_values(controls_0)
#            controls_0 = numpy.zeros( (n_ms, N, n_x) )
#            for i in range(n_ms):
#                e = old_dr(i,grid)
#                controls_0[i,:,:] = e
#    else:
#        controls_0 = numpy.zeros((n_ms, N, n_x))



    controls_0 = numpy.zeros((n_ms, N, n_x))

    if initial_guess is None:
        controls_0[:,:,:] = x0[None,None,:]
    else:
        for i_m in range(n_ms):
            m = P[i_m,:][None,:]
            controls_0[i_m,:,:] = initial_guess(i_m, grid)

    ff = model.functions['arbitrage']
    gg = model.functions['transition']
    aa = model.functions['auxiliary']

    if 'arbitrage_lb' in model.functions and with_complementarities==True:
        lb_fun = model.functions['arbitrage_lb']
        ub_fun = model.functions['arbitrage_ub']
        lb = numpy.zeros_like(controls_0)*numpy.nan
        ub = numpy.zeros_like(controls_0)*numpy.nan
        for i_m in range(n_ms):
            m = P[i_m,:][None,:]
            p = parms[None,:]
            m = numpy.repeat(m, N, axis=0)
            p = numpy.repeat(p, N, axis=0)

            lb[i_m,:,:] = lb_fun(m, grid, p)
            ub[i_m,:,:] = ub_fun(m, grid, p)

    else:
        with_complementarities = False


    f = lambda m,s,x,M,S,X,p: ff(m,s,x,aa(m,s,x,p),M,S,X,aa(M,S,X,p),p)
    g = lambda m,s,x,M,p: gg(m,s,x,aa(m,s,x,p),M,p)

    # mdr.set_values(controls)

    sh_c = controls_0.shape

    controls_0 = controls_0.reshape( (-1,n_x) )


    from dolo.numeric.optimize.newton import newton, SerialDifferentiableFunction
    from dolo.numeric.optimize.ncpsolve import ncpsolve

    err = 10
    tol = 1e-8
    inner_maxit = 50
    it = 0


    if with_complementarities:
        print("Solving WITH complementarities.")
        lb = lb.reshape((-1,n_x))
        ub = ub.reshape((-1,n_x))


    if verbose:
        headline = '|{0:^4} | {1:10} | {2:8} | {3:8} | {4:3} |'.format( 'N',' Error', 'Gain','Time',  'nit' )
        stars = '-'*len(headline)
        print(stars)
        print(headline)
        print(stars)

    import time
    t1 = time.time()

    err_0 = numpy.nan

    verbit = (verbose == 'full')

    while err>tol and it<maxit:

        it += 1

        t_start = time.time()

        mdr.set_values(controls_0.reshape(sh_c))

        fn = lambda x: residuals(f, g, grid, x.reshape(sh_c), mdr, P, Q, parms).reshape((-1,n_x))
        dfn = SerialDifferentiableFunction(fn)

        if with_complementarities:
            [controls,nit] = ncpsolve(dfn, lb, ub, controls_0, verbose=verbit, maxit=inner_maxit)
        else:
            [controls, nit] = newton(dfn, controls_0, verbose=verbit, maxit=inner_maxit)

        err = abs(controls-controls_0).max()

        err_SA = err/err_0
        err_0 = err

        controls_0 = controls

        t_finish = time.time()
        elapsed = t_finish - t_start

        if verbose:
            print('|{0:4} | {1:10.3e} | {2:8.3f} | {3:8.3f} | {4:3} |'.format( it, err, err_SA, elapsed, nit  ))

    controls_0 = controls.reshape(sh_c)

    t2 = time.time()

    if verbose:
        print(stars)
        print("Elapsed: {} seconds.".format(t2-t1))
        print(stars)


    if output_type == 'dr':
        return mdr
    elif output_type == 'controls':
        return controls_0
    else:
        raise Exception("Unsupported ouput type {}.".format(output_type))






if __name__ == '__main__':

    from dolo import *
    model = yaml_import("../../../examples/models/rbc_mfga.yaml")
    print(model.calibration['states'])
    print(model.calibration_dict)
    print(model.markov_chain)


    initial_guess_symbolic = [
        'i = delta*k',
        'n = 0.33'
    ]

    from dolo.compiler.function_compiler_ast import compile_function_ast
    from dolo.compiler.function_compiler import standard_function

    arg_names = [
        ['markov_states',0,'m'],
        ['states',0,'s'],
        ['parameters',0,'p']
    ]

    fun = compile_function_ast(initial_guess_symbolic, model.symbols, arg_names,'initial_guess')
    ff = standard_function(fun, len(initial_guess_symbolic))

    sol = solve_mfg_model(model, initial_guess=ff)
