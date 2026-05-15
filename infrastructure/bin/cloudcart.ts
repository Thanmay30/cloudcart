#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { CloudCartStack } from '../lib/cloudcart-stack';

const app = new cdk.App();
new CloudCartStack(app, 'CloudCartStack', {
  description: 'CloudCart — Serverless Order Processing System on AWS',
});
