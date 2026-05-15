import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { ApiConstruct } from './constructs/api-construct';
import { DatabaseConstruct } from './constructs/database-construct';
import { LambdaConstruct } from './constructs/lambda-construct';
import { QueueConstruct } from './constructs/queue-construct';

export class CloudCartStack extends cdk.Stack {
  public readonly httpApiUrl: string;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const removalPolicy = cdk.RemovalPolicy.DESTROY;

    const database = new DatabaseConstruct(this, 'Database', {
      removalPolicy,
    });

    const queues = new QueueConstruct(this, 'Queues', {
      removalPolicy,
    });

    const lambdas = new LambdaConstruct(this, 'Lambdas', {
      removalPolicy,
      ordersTable: database.ordersTable,
      idempotencyTable: database.idempotencyTable,
      orderProcessingQueue: queues.orderProcessingQueue,
    });

    const api = new ApiConstruct(this, 'Api', {
      createOrderFn: lambdas.createOrderFn,
      getOrderFn: lambdas.getOrderFn,
      getUserOrdersFn: lambdas.getUserOrdersFn,
      cancelOrderFn: lambdas.cancelOrderFn,
    });

    this.httpApiUrl = api.httpApi.apiEndpoint;

    new cdk.CfnOutput(this, 'CloudCartHttpApiUrl', {
      description: 'Invoke the CloudCart HTTP API at this URL',
      value: api.httpApi.apiEndpoint,
    });

    new cdk.CfnOutput(this, 'OrdersTableName', {
      value: database.ordersTable.tableName,
    });

    new cdk.CfnOutput(this, 'IdempotencyTableName', {
      value: database.idempotencyTable.tableName,
    });

    new cdk.CfnOutput(this, 'OrderProcessingQueueUrl', {
      value: queues.orderProcessingQueue.queueUrl,
    });
  }
}
