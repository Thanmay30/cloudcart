import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface DatabaseConstructProps {
  readonly removalPolicy: cdk.RemovalPolicy;
}

export class DatabaseConstruct extends Construct {
  public readonly ordersTable: dynamodb.Table;
  public readonly idempotencyTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: DatabaseConstructProps) {
    super(scope, id);

    this.ordersTable = new dynamodb.Table(this, 'Orders', {
      partitionKey: { name: 'orderId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.removalPolicy,
    });

    this.ordersTable.addGlobalSecondaryIndex({
      indexName: 'userId-createdAt-index',
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'createdAt', type: dynamodb.AttributeType.STRING },
    });

    this.idempotencyTable = new dynamodb.Table(this, 'Idempotency', {
      partitionKey: {
        name: 'idempotencyKeyHash',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.removalPolicy,
      timeToLiveAttribute: 'expiresAt',
    });
  }
}
