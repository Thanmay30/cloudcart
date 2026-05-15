import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

export interface LambdaConstructProps {
  readonly removalPolicy: cdk.RemovalPolicy;
  readonly ordersTable: dynamodb.ITable;
  readonly idempotencyTable: dynamodb.ITable;
  readonly orderProcessingQueue: sqs.IQueue;
}

export class LambdaConstruct extends Construct {
  public readonly createOrderFn: lambda.Function;
  public readonly getOrderFn: lambda.Function;
  public readonly getUserOrdersFn: lambda.Function;
  public readonly cancelOrderFn: lambda.Function;
  public readonly processOrderFn: lambda.Function;

  constructor(scope: Construct, id: string, props: LambdaConstructProps) {
    super(scope, id);

    const src = path.join(__dirname, '../../../src');

    const createLog = new logs.LogGroup(this, 'CreateOrderLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: props.removalPolicy,
    });
    const getOrderLog = new logs.LogGroup(this, 'GetOrderLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: props.removalPolicy,
    });
    const getUserOrdersLog = new logs.LogGroup(this, 'GetUserOrdersLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: props.removalPolicy,
    });
    const cancelLog = new logs.LogGroup(this, 'CancelOrderLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: props.removalPolicy,
    });
    const processLog = new logs.LogGroup(this, 'ProcessOrderLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: props.removalPolicy,
    });

    const commonEnv = {
      ORDERS_TABLE_NAME: props.ordersTable.tableName,
      IDEMPOTENCY_TABLE_NAME: props.idempotencyTable.tableName,
      PAYMENT_FAILURE_RATE: '0.2',
    };

    this.createOrderFn = new lambda.Function(this, 'CreateOrder', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handlers.create_order.handler',
      code: lambda.Code.fromAsset(src),
      timeout: cdk.Duration.seconds(10),
      logGroup: createLog,
      environment: {
        ...commonEnv,
        ORDER_PROCESSING_QUEUE_URL: props.orderProcessingQueue.queueUrl,
      },
    });

    this.getOrderFn = new lambda.Function(this, 'GetOrder', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handlers.get_order.handler',
      code: lambda.Code.fromAsset(src),
      timeout: cdk.Duration.seconds(5),
      logGroup: getOrderLog,
      environment: { ...commonEnv },
    });

    this.getUserOrdersFn = new lambda.Function(this, 'GetUserOrders', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handlers.get_user_orders.handler',
      code: lambda.Code.fromAsset(src),
      timeout: cdk.Duration.seconds(10),
      logGroup: getUserOrdersLog,
      environment: { ...commonEnv },
    });

    this.cancelOrderFn = new lambda.Function(this, 'CancelOrder', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handlers.cancel_order.handler',
      code: lambda.Code.fromAsset(src),
      timeout: cdk.Duration.seconds(10),
      logGroup: cancelLog,
      environment: { ...commonEnv },
    });

    this.processOrderFn = new lambda.Function(this, 'ProcessOrder', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handlers.process_order.handler',
      code: lambda.Code.fromAsset(src),
      timeout: cdk.Duration.seconds(30),
      logGroup: processLog,
      environment: { ...commonEnv },
    });

    props.ordersTable.grantReadWriteData(this.createOrderFn);
    props.idempotencyTable.grantReadWriteData(this.createOrderFn);
    props.orderProcessingQueue.grantSendMessages(this.createOrderFn);

    props.ordersTable.grantReadData(this.getOrderFn);

    props.ordersTable.grantReadData(this.getUserOrdersFn);

    props.ordersTable.grantReadWriteData(this.cancelOrderFn);

    props.ordersTable.grantReadWriteData(this.processOrderFn);

    props.orderProcessingQueue.grantConsumeMessages(this.processOrderFn);

    this.processOrderFn.addEventSource(
      new SqsEventSource(props.orderProcessingQueue, {
        batchSize: 1,
        reportBatchItemFailures: false,
      }),
    );
  }
}
