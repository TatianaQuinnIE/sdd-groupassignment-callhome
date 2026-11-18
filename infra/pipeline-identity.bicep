// The identity the GitHub pipeline signs in with (no passwords).
//
// IE accounts can't create service principals, so the pipeline uses a
// user-assigned managed identity with Contributor on this resource group only.
// GitHub proves who it is with a short-lived token; the federated credentials
// below say which tokens Azure accepts: only runs on the main branch of our repo.
// Deployed once by hand, after main.bicep. Commands are in the README.

targetScope = 'resourceGroup'

param prefix string = 'sdd-3b-g5'
param location string = resourceGroup().location

@description('GitHub repository as owner/name.')
param repo string = 'TatianaQuinnIE/sdd-groupassignment-callhome'

@description('Numeric IDs of the owner and the repository (gh api repos/<owner>/<repo>). GitHub sometimes sends these instead of the names.')
param ownerId string = '232589033'
param repoId string = '1452560487'

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-github'
  location: location
}

// Built-in role ID for Contributor.
var contributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')

resource contributorOnGroup 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, identity.id, contributor)
  properties: {
    roleDefinitionId: contributor
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

var repoName = split(repo, '/')
var subjects = {
  'github-main': 'repo:${repo}:ref:refs/heads/main'
  'github-main-ids': 'repo:${repoName[0]}@${ownerId}/${repoName[1]}@${repoId}:ref:refs/heads/main'
}

// Azure doesn't allow writing two federated credentials of one identity at the
// same time, hence batchSize(1).
@batchSize(1)
resource federated 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = [
  for item in items(subjects): {
    parent: identity
    name: item.key
    properties: {
      issuer: 'https://token.actions.githubusercontent.com'
      subject: item.value
      audiences: [
        'api://AzureADTokenExchange'
      ]
    }
  }
]

output clientId string = identity.properties.clientId
output tenantId string = identity.properties.tenantId
output subscriptionId string = subscription().subscriptionId
