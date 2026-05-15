import * as cdk from 'aws-cdk-lib';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface ApiConstructProps {
  readonly createOrderFn: lambda.IFunction;
  readonly getOrderFn: lambda.IFunction;
  readonly getUserOrdersFn: lambda.IFunction;
  readonly cancelOrderFn: lambda.IFunction;
}

export class ApiConstruct extends Construct {
  public readonly httpApi: apigwv2.HttpApi;

  constructor(scope: Construct, id: string, props: ApiConstructProps) {
    super(scope, id);

    this.httpApi = new apigwv2.HttpApi(this, 'CloudCartHttpApi', {
      apiName: 'cloudcart-http-api',
      description: 'CloudCart order API',
    });

    this.httpApi.addRoutes({
      path: '/orders',
      methods: [apigwv2.HttpMethod.POST],
      integration: new integrations.HttpLambdaIntegration(
        'CreateOrderIntegration',
        props.createOrderFn,
      ),
    });

    this.httpApi.addRoutes({
      path: '/orders/user/{userId}',
      methods: [apigwv2.HttpMethod.GET],
      integration: new integrations.HttpLambdaIntegration(
        'GetUserOrdersIntegration',
        props.getUserOrdersFn,
      ),
    });

    this.httpApi.addRoutes({
      path: '/orders/{orderId}',
      methods: [apigwv2.HttpMethod.GET],
      integration: new integrations.HttpLambdaIntegration(
        'GetOrderIntegration',
        props.getOrderFn,
      ),
    });

    this.httpApi.addRoutes({
      path: '/orders/{orderId}/cancel',
      methods: [apigwv2.HttpMethod.POST],
      integration: new integrations.HttpLambdaIntegration(
        'CancelOrderIntegration',
        props.cancelOrderFn,
      ),
    });
  }
}
