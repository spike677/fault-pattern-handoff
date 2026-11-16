module @jit_standardize attributes {mhlo.num_partitions = 1 : i32, mhlo.num_replicas = 1 : i32} {
  func.func public @main(%arg0: tensor<1x4xf32>) -> (tensor<1x4xf32> {jax.result_info = "result"}) {
    %cst = stablehlo.constant dense<0.000000e+00> : tensor<f32>
    %0 = stablehlo.reduce(%arg0 init: %cst) applies stablehlo.add across dimensions = [1] : (tensor<1x4xf32>, tensor<f32>) -> tensor<1xf32>
    %1 = stablehlo.broadcast_in_dim %0, dims = [0] : (tensor<1xf32>) -> tensor<1x1xf32>
    %cst_0 = stablehlo.constant dense<4.000000e+00> : tensor<f32>
    %2 = stablehlo.broadcast_in_dim %cst_0, dims = [] : (tensor<f32>) -> tensor<1x1xf32>
    %3 = stablehlo.divide %1, %2 : tensor<1x1xf32>
    %4 = stablehlo.multiply %arg0, %arg0 : tensor<1x4xf32>
    %cst_1 = stablehlo.constant dense<0.000000e+00> : tensor<f32>
    %5 = stablehlo.reduce(%4 init: %cst_1) applies stablehlo.add across dimensions = [1] : (tensor<1x4xf32>, tensor<f32>) -> tensor<1xf32>
    %6 = stablehlo.broadcast_in_dim %5, dims = [0] : (tensor<1xf32>) -> tensor<1x1xf32>
    %7 = stablehlo.broadcast_in_dim %cst_0, dims = [] : (tensor<f32>) -> tensor<1x1xf32>
    %8 = stablehlo.divide %6, %7 : tensor<1x1xf32>
    %9 = stablehlo.multiply %3, %3 : tensor<1x1xf32>
    %10 = stablehlo.subtract %8, %9 : tensor<1x1xf32>
    %11 = stablehlo.broadcast_in_dim %3, dims = [0, 1] : (tensor<1x1xf32>) -> tensor<1x4xf32>
    %12 = stablehlo.subtract %arg0, %11 : tensor<1x4xf32>
    %cst_2 = stablehlo.constant dense<9.99999974E-6> : tensor<f32>
    %13 = stablehlo.broadcast_in_dim %cst_2, dims = [] : (tensor<f32>) -> tensor<1x1xf32>
    %14 = stablehlo.add %10, %13 : tensor<1x1xf32>
    %15 = stablehlo.rsqrt %14 : tensor<1x1xf32>
    %16 = stablehlo.broadcast_in_dim %15, dims = [0, 1] : (tensor<1x1xf32>) -> tensor<1x4xf32>
    %17 = stablehlo.multiply %12, %16 : tensor<1x4xf32>
    return %17 : tensor<1x4xf32>
  }
}
