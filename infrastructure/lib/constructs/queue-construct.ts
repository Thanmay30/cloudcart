import * as cdk from 'aws-cdk-lib';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

export interface QueueConstructProps {
  readonly removalPolicy: cdk.RemovalPolicy;
}

export class QueueConstruct extends Construct {
  public readonly orderProcessingDlq: sqs.Queue;
  public readonly orderProcessingQueue: sqs.Queue;

  constructor(scope: Construct, id: string, props: QueueConstructProps) {
    super(scope, id);

    this.orderProcessingDlq = new sqs.Queue(this, 'OrderProcessingDLQ', {
      retentionPeriod: cdk.Duration.days(14),
      removalPolicy: props.removalPolicy,
    });

    this.orderProcessingQueue = new sqs.Queue(this, 'OrderProcessingQueue', {
      visibilityTimeout: cdk.Duration.seconds(120),
      deadLetterQueue: {
        queue: this.orderProcessingDlq,
        maxReceiveCount: 3,
      },
      removalPolicy: props.removalPolicy,
    });
  }
}
