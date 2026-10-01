import tenseal as ts


def roundtrip(value):
    context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                         coeff_mod_bit_sizes=[60, 40, 40, 60], n_threads=2)
    context.global_scale = 2**40
    return ts.ckks_vector(context, [value]).decrypt()[0]
